import json
from types import SimpleNamespace

import pytest
from fastapi import FastAPI

from demo_fixture import NOW
from midflight.adapters.clock import FixedClock
from midflight.adapters.memory_store import MemoryStore
from midflight.api.app import build_services
from midflight.theater.delivery_fixture import DeliveryTheater, initial_plan
from midflight.theater.resume import restore
from midflight.theater.scenario import seed


def saved_run(tmp_path, monkeypatch):
    services = build_services(MemoryStore(), FixedClock(NOW))
    tokens = seed(services, "demo", initial_plan())
    names = ["billing", "delivery", "booking", "notifications"]
    metadata = {
        "session": "saved-session",
        "project": "demo",
        "panes": {n: f"%{i}" for i, n in enumerate(names)},
    }
    (tmp_path / "interactive.json").write_text(json.dumps(metadata))
    (tmp_path / "report.json").write_text(json.dumps({"direction": None, "visual_events": []}))
    for name in names:
        config = (
            "mcp_servers.theater_midflight={env={"
            + ",".join(
                json.dumps(k) + "=" + json.dumps(v)
                for k, v in {
                    "MIDFLIGHT_PROJECT": "demo",
                    "MIDFLIGHT_URL": "http://127.0.0.1:8910",
                    "MIDFLIGHT_DEMO_CONTROLLER": "http://127.0.0.1:8909",
                    "MIDFLIGHT_TOKEN": tokens[name],
                }.items()
            )
            + "}}"
        )
        (tmp_path / f"{name}-launch.json").write_text(json.dumps(["codex", "-c", config]))
    monkeypatch.setattr(
        "midflight.theater.resume.create_server",
        lambda *a, **kw: SimpleNamespace(services=services, app=FastAPI()),
    )
    monkeypatch.setattr(DeliveryTheater, "tmux", lambda *a: "")
    monkeypatch.setattr(
        "midflight.theater.resume.subprocess.check_output",
        lambda *a, **kw: "runtime-sha\n" if kw.get("text") else b"",
    )
    return services, metadata


def test_restore_preserves_graph_identities_session_and_saved_files(tmp_path, monkeypatch):
    services, metadata = saved_run(tmp_path, monkeypatch)
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    project = services.store.get_project("demo").model_dump()
    monkeypatch.setattr(DeliveryTheater, "launch", lambda *a: pytest.fail("must not launch agents"))
    live = restore(tmp_path)
    assert live.session == metadata["session"]
    assert live.panes == metadata["panes"]
    assert services.store.get_project("demo").model_dump() == project
    assert {p.name: p.read_bytes() for p in tmp_path.iterdir()} == before
    assert not live.theater.api.started
    assert not live.theater.api_thread.is_alive()
    assert len(live.theater.tokens) == 4


def test_restore_refuses_changed_ports_and_revoked_local_token(tmp_path, monkeypatch):
    services, _ = saved_run(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match="ports/project"):
        restore(tmp_path, port=8999)
    file = tmp_path / "billing-launch.json"
    args = json.loads(file.read_text())
    args[-1] = args[-1].replace('MIDFLIGHT_TOKEN"=', 'MIDFLIGHT_TOKEN"="wrong", "old"=')
    file.write_text(json.dumps(args))
    with pytest.raises(ValueError, match="identity"):
        restore(tmp_path)
