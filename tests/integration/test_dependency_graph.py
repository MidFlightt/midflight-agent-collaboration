import pytest

from demo_fixture import PROJECT, seed
from midflight.domain.models import Contract, FieldType, Plan, Task
from midflight.ports import Commit


def plan(version=2, *, remove=False, cycle=False):
    tasks = [
        Task(id=t, title=t, owner="p-t1")
        for t in ["pricing", "checkout", "reporting", "notifications"]
    ]
    contracts = [
        Contract(
            id="price",
            version=version,
            provider_task="pricing",
            consumer_tasks=[] if remove else ["checkout"],
            fields={"amount": FieldType.INTEGER},
        ),
        Contract(
            id="order",
            version=version,
            provider_task="checkout",
            consumer_tasks=["reporting"],
            fields={"amount": FieldType.INTEGER},
        ),
    ]
    if cycle:
        contracts.append(
            Contract(
                id="summary",
                version=version,
                provider_task="reporting",
                consumer_tasks=["pricing"],
                fields={"amount": FieldType.INTEGER},
            )
        )
    return Plan(project_id=PROJECT, version=version, tasks=tasks, contracts=contracts)


def save(store, value, key="plan"):
    store.commit(Commit(PROJECT, key, puts=[value]))


def test_direct_and_downstream_evidence_excludes_unrelated_task(falkor_store):
    seed(falkor_store)
    save(falkor_store, plan())
    result = falkor_store.dependency_impact(PROJECT, 2, 2, ["price"])
    assert set(result.affected_tasks) == {"pricing", "checkout", "reporting"}
    path = next(p for p in result.paths if p.task_id == "reporting")
    assert [n.item_id for n in path.nodes] == ["price", "checkout", "order", "reporting"]
    assert path.plan_version == 2


def test_removed_dependency_uses_old_graph(falkor_store):
    seed(falkor_store)
    save(falkor_store, plan(), "old")
    save(falkor_store, plan(3, remove=True), "new")
    result = falkor_store.dependency_impact(PROJECT, 2, 3, ["price"])
    assert "reporting" in result.affected_tasks
    assert all(p.plan_version == 2 for p in result.paths if p.task_id == "reporting")


def test_draft_replacement_does_not_leave_stale_paths(falkor_store):
    seed(falkor_store)
    save(falkor_store, plan(), "before")
    save(falkor_store, plan(remove=True), "after")
    result = falkor_store.dependency_impact(PROJECT, 2, 2, ["price"])
    assert set(result.affected_tasks) == {"pricing"}


def test_cycles_terminate_and_limits_fail_explicitly(falkor_store):
    from midflight.domain.graph import IncompleteImpact

    seed(falkor_store)
    save(falkor_store, plan(cycle=True))
    result = falkor_store.dependency_impact(PROJECT, 2, 2, ["price"])
    assert set(result.affected_tasks) == {"pricing", "checkout", "reporting"}
    with pytest.raises(IncompleteImpact):
        falkor_store.dependency_impact(PROJECT, 2, 2, ["price"], max_depth=1)
    with pytest.raises(IncompleteImpact):
        falkor_store.dependency_impact(PROJECT, 2, 2, ["price"], max_edges=1)


def test_missing_graph_is_not_empty_impact(falkor_store):
    from midflight.domain.graph import GraphNotReady

    seed(falkor_store)
    with pytest.raises(GraphNotReady):
        falkor_store.dependency_impact(PROJECT, 2, 3, ["price"])


def test_projection_is_atomic_with_plan_and_rollback(falkor_store, monkeypatch):
    from redis.exceptions import ResponseError

    seed(falkor_store)
    before = plan()
    save(falkor_store, before)
    snapshots = falkor_store._query("MATCH (g:MFPlanGraph) RETURN count(g)")
    query = falkor_store._query

    def fail(text, params):
        return query(
            text.replace(") RETURN outcome", "SET target.invalid=$invalid ) RETURN outcome"),
            {**params, "invalid": {"map": "invalid property"}},
        )

    with monkeypatch.context() as patch:
        patch.setattr(falkor_store, "_query", fail)
        with pytest.raises(ResponseError):
            save(falkor_store, plan(remove=True), "bad")
    assert falkor_store.get_plan(PROJECT, 2) == before
    assert falkor_store._query("MATCH (g:MFPlanGraph) RETURN count(g)") == snapshots
    assert "reporting" in falkor_store.dependency_impact(PROJECT, 2, 2, ["price"]).affected_tasks


def test_paths_never_combine_edges_from_different_versions(falkor_store):
    seed(falkor_store)
    old = plan().model_copy(update={"contracts": [plan().contracts[0]]})
    save(falkor_store, old, "old")
    save(falkor_store, plan(3, remove=True), "new")
    result = falkor_store.dependency_impact(PROJECT, 2, 3, ["price"])
    assert set(result.affected_tasks) == {"pricing", "checkout"}


def test_project_isolation_with_identical_task_ids(falkor_store):
    from midflight.domain.models import Project

    seed(falkor_store)
    save(falkor_store, plan())
    other = plan(remove=True).model_copy(update={"project_id": "other"})
    falkor_store.commit(
        Commit(
            "other",
            "other",
            puts=[Project(id="other", repository="other/repo", lead_id="lead"), other],
        )
    )
    assert set(falkor_store.dependency_impact("other", 2, 2, ["price"]).affected_tasks) == {
        "pricing"
    }
    assert "reporting" in falkor_store.dependency_impact(PROJECT, 2, 2, ["price"]).affected_tasks


def test_removed_tasks_are_not_recipients_but_downstream_tasks_are(falkor_store):
    seed(falkor_store)
    save(falkor_store, plan(), "old")
    new = plan(3).model_copy(
        update={"tasks": [t for t in plan(3).tasks if t.id != "checkout"], "contracts": []}
    )
    save(falkor_store, new, "new")
    result = falkor_store.dependency_impact(PROJECT, 2, 3, ["checkout"])
    assert set(result.affected_tasks) == {"reporting"}


def test_backfill_approved_plan_is_idempotent_and_preserves_revision(falkor_store):
    from midflight.domain.graph import GraphNotReady

    seed(falkor_store)
    # Simulate the pre-materialization schema using an existing immutable plan.
    falkor_store._query("MATCH (p:MFPlan) REMOVE p.graph_key")
    with pytest.raises(GraphNotReady):
        falkor_store.dependency_impact(PROJECT, 1, 1, [])
    revision = falkor_store.get_project(PROJECT).coord_rev
    assert falkor_store.materialize_approved_plan(PROJECT, 1).applied
    assert falkor_store.materialize_approved_plan(PROJECT, 1).duplicate
    assert falkor_store.dependency_impact(PROJECT, 1, 1, []).paths == ()
    assert falkor_store.get_project(PROJECT).coord_rev == revision


def test_draft_change_during_traversal_is_reported(falkor_store, monkeypatch):
    from midflight.domain.graph import GraphChanged

    seed(falkor_store)
    save(falkor_store, plan())
    query = falkor_store._query
    changed = False

    def interleave(text, params=None):
        nonlocal changed
        result = query(text, params)
        if "RETURN n.item_id LIMIT" in text and not changed:
            changed = True
            save(falkor_store, plan(remove=True), "edit")
        return result

    monkeypatch.setattr(falkor_store, "_query", interleave)
    with pytest.raises(GraphChanged):
        falkor_store.dependency_impact(PROJECT, 2, 2, ["price"])


def test_requirement_propagation_and_unknown_changes(falkor_store):
    from midflight.domain.models import Requirement

    seed(falkor_store)
    value = plan()
    tasks = [
        t.model_copy(update={"requirement_ids": ["R-price"]}) if t.id == "pricing" else t
        for t in value.tasks
    ]
    value = value.model_copy(
        update={"tasks": tasks, "requirements": [Requirement(id="R-price", description="currency")]}
    )
    save(falkor_store, value)
    result = falkor_store.dependency_impact(PROJECT, 2, 2, ["R-price"])
    assert set(result.affected_tasks) == {"pricing", "checkout", "reporting"}
    with pytest.raises(ValueError, match="absent"):
        falkor_store.dependency_impact(PROJECT, 2, 2, ["typo"])


def test_dangling_reference_rejects_plan_and_graph_atomically(falkor_store):
    seed(falkor_store)
    value = plan()
    invalid = value.model_copy(
        update={
            "contracts": [
                value.contracts[0].model_copy(update={"consumer_tasks": ["missing-task"]})
            ]
        }
    )
    with pytest.raises(ValueError, match="unknown graph reference"):
        save(falkor_store, invalid, "invalid")
    assert falkor_store.get_plan(PROJECT, 2) is None
    assert falkor_store._query("MATCH (g:MFPlanGraph) RETURN count(g)") == [[1]]
    assert save(falkor_store, value, "invalid") is None  # rejected receipt was not saved
    assert falkor_store.get_plan(PROJECT, 2) == value


def test_node_limit_and_empty_change_set(falkor_store):
    from midflight.domain.graph import IncompleteImpact

    seed(falkor_store)
    save(falkor_store, plan())
    assert falkor_store.dependency_impact(PROJECT, 2, 2, []).affected_tasks == {}
    with pytest.raises(IncompleteImpact):
        falkor_store.dependency_impact(PROJECT, 2, 2, ["pricing"], max_nodes=4)
    result = falkor_store.dependency_impact(PROJECT, 2, 2, ["price", "price"])
    assert len([p for p in result.paths if p.task_id == "reporting"]) == 1
