import pytest

from demo_fixture import NOW, PROJECT, seed
from midflight.adapters.clock import FixedClock
from midflight.adapters.runners import DeferredRunner
from midflight.api.app import build_services
from midflight.api.views import check_in_json
from midflight.domain.models import Contract, FieldType, Task
from midflight.services.plans import PlanDraft


def setup(store):
    seed(store)
    services = build_services(store, FixedClock(NOW), runner=DeferredRunner())
    lead = store.get_participant("p-lead")
    tasks = [
        Task(id=t, title=t, owner=owner)
        for t, owner in [
            ("pricing", "p-t1"),
            ("checkout", "p-t2"),
            ("reporting", "p-t3"),
            ("notifications", "p-lead"),
        ]
    ]
    contracts = [
        Contract(
            id="price",
            version=2,
            provider_task="pricing",
            consumer_tasks=["checkout"],
            fields={"amount": FieldType.INTEGER},
        ),
        Contract(
            id="order",
            version=2,
            provider_task="checkout",
            consumer_tasks=["reporting"],
            fields={"amount": FieldType.INTEGER},
        ),
    ]
    draft = PlanDraft(tasks=tasks, contracts=contracts, requirements=[])
    services.plans.approve(lead, services.plans.propose(lead, draft).version, "commerce plan")
    # Close setup directives so assertions isolate the next change.
    from midflight.domain.models import DirectiveState
    from midflight.ports import Commit

    store.commit(
        Commit(
            PROJECT,
            "clear-setup",
            puts=[
                d.model_copy(update={"state": DirectiveState.SUPERSEDED})
                for d in store.list_directives(PROJECT)
            ],
        )
    )
    contracts[0] = contracts[0].model_copy(
        update={"fields": {"amount": FieldType.INTEGER, "currency": FieldType.STRING}}
    )
    draft = PlanDraft(tasks=tasks, contracts=contracts, requirements=[])
    pending = services.plans.propose(lead, draft)
    return services, lead, pending


def test_downstream_directive_and_checkin_explain_graph_path(falkor_store):
    from midflight.mcp.replies import check_in_text

    services, lead, pending = setup(falkor_store)
    services.plans.approve(lead, pending.version, "currency-aware prices")
    directives = [
        d for d in falkor_store.list_directives(PROJECT) if d.plan_version == pending.version
    ]
    assert {d.task_id for d in directives} == {"pricing", "checkout", "reporting"}
    reply = services.check_ins.check_in(falkor_store.get_participant("p-t3"), task_id="reporting")
    assert len(reply.directives) == 1
    assert "price" in reply.directives[0].reason and "order" in reply.directives[0].reason
    rendered = check_in_text(check_in_json(reply))
    assert "Graph evidence" in rendered and "reporting" in rendered
    unaffected = services.check_ins.check_in(lead, task_id="notifications")
    assert not unaffected.directives
    fresh = services.check_ins.check_in(falkor_store.get_participant("p-t3"), task_id="reporting")
    assert "Graph evidence" in check_in_text(check_in_json(fresh))


def test_incomplete_graph_prevents_approval_without_partial_writes(falkor_store, monkeypatch):
    from midflight.domain.graph import IncompleteImpact
    from midflight.services.errors import StateConflict

    services, lead, pending = setup(falkor_store)
    before = falkor_store.get_project(PROJECT)
    directives = falkor_store.list_directives(PROJECT)

    def incomplete(*args, **kwargs):
        raise IncompleteImpact("edge limit reached")

    monkeypatch.setattr(falkor_store, "dependency_impact", incomplete)
    with pytest.raises(StateConflict, match="graph impact"):
        services.plans.approve(lead, pending.version, "currency")
    assert falkor_store.get_project(PROJECT) == before
    assert falkor_store.get_plan(PROJECT, pending.version) == pending
    assert falkor_store.list_directives(PROJECT) == directives


def test_draft_edit_after_analysis_retries_with_current_graph(falkor_store, monkeypatch):
    from midflight.ports import Commit

    services, lead, pending = setup(falkor_store)
    original = falkor_store.commit_graph_approval
    changed = False

    def interleave(write, expected_graphs):
        nonlocal changed
        if not changed:
            changed = True
            edited = pending.model_copy(
                update={
                    "contracts": [
                        pending.contracts[0].model_copy(update={"consumer_tasks": []}),
                        pending.contracts[1],
                    ]
                }
            )
            falkor_store.commit(Commit(PROJECT, "edit-during-approval", puts=[edited]))
        return original(write, expected_graphs)

    monkeypatch.setattr(falkor_store, "commit_graph_approval", interleave)
    approved = services.plans.approve(lead, pending.version, "edited currency")
    assert approved.contracts[0].consumer_tasks == []
    reporting = next(
        d
        for d in falkor_store.list_directives(PROJECT)
        if d.plan_version == pending.version and d.task_id == "reporting"
    )
    assert "Graph evidence (plan v2):" in reporting.reason
    assert "Graph evidence (plan v3):" not in reporting.reason
    assert (
        len(
            [
                e
                for e in falkor_store.list_audit(PROJECT)
                if e.action == "plan.approved" and e.versions["plan"] == pending.version
            ]
        )
        == 1
    )


def test_downstream_approved_claim_gets_durable_review_job(falkor_store):
    from demo_fixture import make_claim
    from midflight.domain.models import ClaimState
    from midflight.ports import Commit

    services, lead, pending = setup(falkor_store)
    reporting = make_claim(
        "reporting", id="C-reporting", agent_id="p-t3", plan_version=2, state=ClaimState.APPROVED
    )
    independent = reporting.model_copy(update={"id": "C-independent", "task_id": "notifications"})
    falkor_store.commit(
        Commit(PROJECT, "approved-work", puts=[reporting, independent], bump_coord_rev=True)
    )
    services.plans.approve(lead, pending.version, "currency")
    assert falkor_store.get_claim(reporting.id).state is ClaimState.PENDING
    assert falkor_store.get_claim(independent.id).state is ClaimState.APPROVED
    jobs = falkor_store.list_jobs(PROJECT)
    assert len(jobs) == 1 and reporting.id in jobs[0].subject_id


def test_missing_projection_blocks_approval(falkor_store):
    from midflight.services.errors import StateConflict

    services, lead, pending = setup(falkor_store)
    falkor_store._query("MATCH (p:MFPlan {version:2}) REMOVE p.graph_key")
    with pytest.raises(StateConflict, match="graph impact"):
        services.plans.approve(lead, pending.version, "currency")
    assert falkor_store.get_project(PROJECT).current_plan_version == 2


def test_rejected_snapshot_guard_writes_no_directives_or_receipt(falkor_store):
    from midflight.domain.graph import GraphChanged
    from midflight.ports import Commit

    services, lead, pending = setup(falkor_store)
    before = falkor_store.get_project(PROJECT)
    with pytest.raises(GraphChanged):
        falkor_store.commit_graph_approval(
            Commit(PROJECT, "guarded", bump_coord_rev=True), {pending.version: "obsolete"}
        )
    assert falkor_store.get_project(PROJECT) == before
    assert falkor_store.commit_graph_approval(
        Commit(PROJECT, "guarded", bump_coord_rev=True),
        {pending.version: falkor_store.plan_graph_key(pending)},
    ).applied


def test_concurrent_approval_does_not_dispatch_uncommitted_jobs(falkor_store, monkeypatch):
    from demo_fixture import make_claim
    from midflight.domain.models import ClaimState
    from midflight.ports import Commit
    from midflight.services.errors import StateConflict

    services, lead, pending = setup(falkor_store)
    reporting = make_claim(
        "reporting", id="C-reporting", agent_id="p-t3", plan_version=2, state=ClaimState.APPROVED
    )
    falkor_store.commit(Commit(PROJECT, "work", puts=[reporting], bump_coord_rev=True))
    original = falkor_store.commit_graph_approval
    raced = False

    def competing(write, expected_graphs):
        nonlocal raced
        if not raced:
            raced = True
            services.plans.approve(lead, pending.version, "other request")
        return original(write, expected_graphs)

    monkeypatch.setattr(falkor_store, "commit_graph_approval", competing)
    with pytest.raises(StateConflict, match="already approved"):
        services.plans.approve(lead, pending.version, "first request")
    assert len(falkor_store.list_jobs(PROJECT)) == 1
    assert len(services.plans._runner.pending) == 1
