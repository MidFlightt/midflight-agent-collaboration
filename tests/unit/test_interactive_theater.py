import threading
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from demo_fixture import NOW
from midflight.adapters.clock import FixedClock
from midflight.adapters.memory_store import MemoryStore
from midflight.api.app import build_services
from midflight.domain.models import Role
from midflight.ports import Commit
from midflight.theater.interactive import InteractiveTheater, terminal_app
from midflight.theater.scenario import NAMES, seed


def live_fixture(tmp_path):
    services = build_services(MemoryStore(), FixedClock(NOW))
    tokens = seed(services, "demo")
    actor = services.store.get_participant("pricing").model_copy(update={"role": Role.LEAD})
    services.store.commit(Commit("demo", "promote", puts=[actor]))
    live = InteractiveTheater.__new__(InteractiveTheater)
    live.changed = False
    live.direction = None
    live.version = 1
    live.guard = threading.RLock()
    live.checkpoint_wake = threading.Event()
    live.cues = dict.fromkeys(NAMES, "unchanged")
    live.check_ins = dict.fromkeys(NAMES, 0)
    live.events = []
    live.theater = SimpleNamespace(
        root=tmp_path,
        project="demo",
        tokens=tokens,
        server=SimpleNamespace(services=services),
        save_report=lambda: {"checks": {"application_integration": False}},
    )
    return live


def test_human_direction_can_arrive_during_work_and_is_safe_to_retry(tmp_path):
    live = live_fixture(tmp_path)
    result = live.set_direction("pricing", "We will do subscription based")
    assert result["plan_version"] == 2
    assert live.set_direction("pricing", "We will do subscription based") == {
        "plan_version": 2,
        "direction": "We will do subscription based",
    }
    plan = live.theater.server.services.plans.current("demo")
    assert plan.requirements[0].description == "We will do subscription based"
    assert not plan.task("notifications").requirement_ids
    assert "subscription_id" in plan.contract("order").fields
    assert live.cues["checkout"] == "waiting"
    assert live.cues["notifications"] == "unchanged"
    assert len(live.events) == 1
    with pytest.raises(HTTPException) as error:
        live.set_direction("pricing", "another subscription direction")
    assert error.value.status_code == 409


def test_only_lead_can_apply_supported_direction(tmp_path):
    live = live_fixture(tmp_path)
    for name, text, status in [
        ("checkout", "subscription", 403),
        ("pricing", "", 422),
        ("pricing", "We will sell boats", 422),
    ]:
        with pytest.raises(HTTPException) as error:
            live.set_direction(name, text)
        assert error.value.status_code == status
    assert live.theater.server.services.plans.current("demo").version == 1
    assert not live.events
    with pytest.raises(HTTPException):
        live.actor_for("Bearer wrong")
    assert live.actor_for("Bearer " + live.theater.tokens["pricing"]) == "pricing"


def test_terminal_control_rejects_untrusted_hosts_and_keys():
    live = SimpleNamespace(key="local-demo-key", close=lambda: None)
    with TestClient(terminal_app(live), base_url="http://localhost") as client:
        assert client.get("/connection", headers={"Host": "other.example"}).status_code == 400
        assert (
            client.get("/connection", headers={"Sec-Fetch-Site": "cross-site"}).status_code == 403
        )
        assert client.post("/reset").status_code == 403
        assert client.get("/status").status_code == 403
        assert client.post("/change").status_code == 404
        with (
            pytest.raises(WebSocketDisconnect),
            client.websocket_connect("/terminal?key=wrong", headers={"origin": "http://localhost"}),
        ):
            pass


def test_interactive_report_does_not_treat_live_processes_as_finished(tmp_path):
    live = InteractiveTheater.__new__(InteractiveTheater)
    live.changed = False
    live.direction = None
    live.events = []
    live.session = "test-session"
    live.panes = {"pricing": "%0"}
    live.tmux = lambda *args: "0" if args[-1] == "#{pane_dead}" else "42"
    live.theater = SimpleNamespace(
        root=tmp_path,
        save_report=lambda: {
            "checks": {"all_agents_finished": False},
            "agents": {"pricing": "ready"},
        },
    )
    report = live.report()
    assert "all_agents_finished" not in report["checks"]
    assert report["checks"]["sessions_alive"]
    assert report["agents"]["pricing"]["pid"] == "42"


def test_reset_archives_old_run_and_replaces_sessions_and_key(tmp_path, monkeypatch):
    import midflight.theater.interactive as module

    calls = []
    old = SimpleNamespace(
        key="old-key",
        controller_port=8897,
        theater=SimpleNamespace(root=tmp_path / "old", db_port=6379, api_port=8898),
        report=lambda: calls.append("archive"),
        close=lambda: calls.append("close-old"),
    )

    def factory(root, db, api, controller):
        assert root != old.theater.root
        assert (db, api, controller) == (6379, 8898, 8897)
        return SimpleNamespace(
            key="new-key",
            session="fresh",
            theater=SimpleNamespace(commit="abc123"),
            launch=lambda: calls.append("launch"),
            close=lambda: calls.append("close-new"),
        )

    monkeypatch.setattr(module, "InteractiveTheater", factory)
    with TestClient(terminal_app(old), base_url="http://localhost") as client:
        assert client.post("/reset", headers={"x-demo-key": "old-key"}).json()["session"] == "fresh"
        assert calls == ["archive", "close-old", "launch"]
        assert client.get("/connection").json()["key"] == "new-key"
        assert client.post("/reset", headers={"x-demo-key": "old-key"}).status_code == 403
    assert calls[-1] == "close-new"


def test_observed_check_in_colors_only_affected_agents(tmp_path):
    live = live_fixture(tmp_path)
    live.set_direction("pricing", "We will do subscription based")
    services = live.theater.server.services
    for name in NAMES:
        services.check_ins.check_in(services.store.get_participant(name), task_id=name)
        live.observed(name)
    assert live.cues["checkout"] == "received"
    assert live.cues["reporting"] == "received"
    assert live.cues["notifications"] == "unchanged"
    assert all(count == 1 for count in live.check_ins.values())


def test_cue_layout_follows_real_pane_geometry_after_resize():
    live = InteractiveTheater.__new__(InteractiveTheater)
    live.session, live.panes = "test", {"pricing": "%0", "reporting": "%2"}
    live.tmux = lambda *args: "%0 0 1 74 25\n%2 0 27 74 29"
    assert live.layout()["reporting"] == {"x": 0, "y": 27, "width": 74, "height": 29}
