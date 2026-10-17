from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from midflight.theater.interactive import InteractiveTheater, terminal_app


def test_change_is_refused_before_independent_initial_acceptance():
    live = InteractiveTheater.__new__(InteractiveTheater)
    live.changed = False
    live.theater = SimpleNamespace(
        save_report=lambda: {
            "checks": {
                "four_claims": True,
                "all_claims_approved": True,
                "application_integration": False,
            }
        }
    )
    with pytest.raises(HTTPException) as error:
        live.introduce_change()
    assert error.value.status_code == 409
    assert not live.changed


def test_terminal_control_rejects_untrusted_hosts_and_keys():
    live = SimpleNamespace(key="local-demo-key", close=lambda: None)
    with TestClient(terminal_app(live), base_url="http://localhost") as client:
        assert client.get("/connection", headers={"Host": "other.example"}).status_code == 400
        assert (
            client.get("/connection", headers={"Sec-Fetch-Site": "cross-site"}).status_code == 403
        )
        assert client.post("/change").status_code == 403
        with (
            pytest.raises(WebSocketDisconnect),
            client.websocket_connect("/terminal?key=wrong", headers={"origin": "http://localhost"}),
        ):
            pass


def test_interactive_report_does_not_treat_live_processes_as_finished(tmp_path):
    live = InteractiveTheater.__new__(InteractiveTheater)
    live.changed = True
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
    assert report["phase"] == "changed"
