"""Run the demo's actual scenario through FalkorDB, without paid agent sessions."""

from types import SimpleNamespace

from demo_fixture import NOW
from midflight.adapters.clock import FixedClock
from midflight.api.app import build_services
from midflight.api.views import check_in_json
from midflight.domain.models import DirectiveResponse, DirectiveState
from midflight.mcp.replies import check_in_text
from midflight.theater.app import Theater
from midflight.theater.scenario import NAMES, change, seed


def test_demo_price_change_delivers_downstream_evidence(falkor_store, tmp_path):
    services = build_services(falkor_store, FixedClock(NOW))
    seed(services, "demo")
    before = services.plans.current("demo")
    change(services, "demo")
    after = services.plans.current("demo")
    # Reporting is not edited or named in the change. Its dependency path must select it.
    assert after.task("reporting") == before.task("reporting")
    assert after.contract("order").model_dump(exclude={"version"}) == before.contract(
        "order"
    ).model_dump(exclude={"version"})
    assert after.changed_ids == ["price"]
    directives = falkor_store.list_directives("demo")
    assert {d.task_id for d in directives} == {"pricing", "checkout", "reporting"}
    assert all(d.state is DirectiveState.QUEUED for d in directives)
    for name in NAMES:
        actor = falkor_store.get_participant(name)
        reply = services.check_ins.check_in(actor, task_id=name)
        if name == "notifications":
            assert not reply.directives
            continue
        directive = reply.directives[0]
        assert directive.state is DirectiveState.DELIVERED
        assert "Graph evidence" in check_in_text(check_in_json(reply))
        if name == "reporting":
            assert (
                "contract price -CONSUMED_BY-> task checkout -PROVIDES-> contract order "
                "-CONSUMED_BY-> task reporting"
            ) in directive.reason
        services.directives.acknowledge(actor, directive.id, DirectiveResponse.ACKNOWLEDGED)
    # Use the same report builder displayed by the interactive demo.
    theater = Theater.__new__(Theater)
    theater.server = SimpleNamespace(services=services)
    theater.project = "demo"
    theater.root = tmp_path
    theater.status = dict.fromkeys(NAMES, "done")
    theater.changed = True
    theater.phase = "changed"
    theater.baseline_hash = None
    theater.commit = "test"
    theater.dirty = False
    theater.integration = lambda: {"passed": True}
    report = theater.save_report()
    assert report["checks"]["reporting_notified"]
    assert report["checks"]["graph_evidence_saved"]
    assert report["checks"]["affected_agents_acknowledged"]
    assert report["checks"]["notifications_unaffected"]
