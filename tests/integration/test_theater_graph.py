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


def test_manual_subscription_direction_and_cues_use_saved_graph_state(falkor_store, tmp_path):
    import threading

    from fastapi.testclient import TestClient

    from midflight.domain.models import Role
    from midflight.ports import Commit
    from midflight.theater.interactive import InteractiveTheater, terminal_app

    services = build_services(falkor_store, FixedClock(NOW))
    tokens = seed(services, "demo")
    actor = falkor_store.get_participant("pricing").model_copy(update={"role": Role.LEAD})
    falkor_store.commit(Commit("demo", "demo-lead", puts=[actor]))
    live = InteractiveTheater.__new__(InteractiveTheater)
    live.changed, live.direction, live.version = False, None, 1
    live.guard = threading.RLock()
    live.checkpoint_wake = threading.Event()
    live.cues = dict.fromkeys(NAMES, "unchanged")
    live.check_ins = dict.fromkeys(NAMES, 0)
    live.events = []
    live.close = lambda: None
    live.theater = SimpleNamespace(
        root=tmp_path,
        project="demo",
        tokens=tokens,
        server=SimpleNamespace(services=services),
        save_report=lambda: {},
    )
    with TestClient(terminal_app(live), base_url="http://localhost") as client:

        def headers(name):
            return {"Authorization": "Bearer " + tokens[name]}

        body = {"direction": "We will do subscription based"}
        assert client.post("/direction", headers=headers("checkout"), json=body).status_code == 403
        result = client.post("/direction", headers=headers("pricing"), json=body)
        assert result.status_code == 200 and result.json()["plan_version"] == 2
        assert client.post("/direction", headers=headers("pricing"), json=body).status_code == 200
        assert len(live.events) == 1
        # A telemetry request alone cannot prove that the agent received a queued directive.
        client.post("/observed", headers=headers("reporting"))
        assert live.cues["reporting"] == "waiting"
        for name in NAMES:
            actor = falkor_store.get_participant(name)
            reply = services.check_ins.check_in(actor, task_id=name)
            client.post("/observed", headers=headers(name))
            if name == "notifications":
                assert not reply.directives and live.cues[name] == "unchanged"
                continue
            assert live.cues[name] == "received"
            assert "Graph evidence" in check_in_text(check_in_json(reply))
            services.directives.acknowledge(
                actor, reply.directives[0].id, DirectiveResponse.ACKNOWLEDGED
            )
            services.check_ins.check_in(actor, task_id=name)
            client.post("/observed", headers=headers(name))
            assert live.cues[name] == "acknowledged"
