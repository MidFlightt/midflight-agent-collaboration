from types import SimpleNamespace

from fastapi.testclient import TestClient

from demo_fixture import make_claim
from midflight.domain.models import FieldType, InterfaceUse
from midflight.theater.live_graph import snapshot
from midflight.theater.peers import peer_app


def fake_live(claims=(), arrivals=()):
    graph = SimpleNamespace(query=lambda *args: SimpleNamespace(result_set=list(arrivals)))
    store = SimpleNamespace(
        graph=graph, list_claims=lambda p: list(claims), list_directives=lambda p: []
    )
    return SimpleNamespace(
        key="secret",
        version=1,
        panes={},
        close=lambda: None,
        theater=SimpleNamespace(
            project="demo", server=SimpleNamespace(services=SimpleNamespace(store=store))
        ),
    )


def test_seeded_plan_does_not_populate_the_blank_workspace():
    result = snapshot(fake_live())
    assert result["nodes"] == result["edges"] == []
    assert not result["started"]
    result = snapshot(fake_live(arrivals=[("alice", "now")]))
    assert [(n["kind"], n["label"]) for n in result["nodes"]] == [("agent", "alice")]
    assert result["edges"] == []


def test_claims_share_interfaces_and_removed_declarations_disappear():
    interface = InterfaceUse(contract_id="price", fields={"total_cents": FieldType.INTEGER})
    old = make_claim("T1", agent_id="alice", provides=[interface], consumes=[], files=["old.py"])
    new = old.model_copy(update={"revision": 2, "files": ["new.py"]})
    consumer = make_claim("T2", agent_id="bob", consumes=[interface])
    result = snapshot(fake_live([old, consumer, new]))
    nodes = {n["id"]: n for n in result["nodes"]}
    assert [n["label"] for n in nodes.values() if n["kind"] == "interface"] == ["price"]
    assert "file:T1:old.py" not in nodes
    assert "file:T1:new.py" in nodes
    edges = [e for e in result["edges"] if e["target"] == "interface:price"]
    assert {e["kind"] for e in edges} == {"provides", "consumes"}
    assert all(e["fields"] == {"total_cents": "integer"} for e in edges)
    assert all(e["source"] in nodes and e["target"] in nodes for e in result["edges"])


def test_graph_reads_and_start_require_the_current_run_key():
    live = fake_live()
    calls = []
    live.launch = lambda: (calls.append("launch"), live.panes.update({"alice": "%0"}))
    with TestClient(peer_app(live), base_url="http://localhost") as client:
        assert client.get("/graph-state").status_code == 403
        assert client.post("/peer-start").status_code == 403
        assert client.get("/graph-state", headers={"x-demo-key": "secret"}).json()["nodes"] == []
        for _ in range(2):
            assert client.post("/peer-start", headers={"x-demo-key": "secret"}).status_code == 200
        assert calls == ["launch"]


def test_staged_reset_archives_run_and_waits_for_start(tmp_path):
    from midflight.theater.interactive import terminal_app

    calls = []
    old = SimpleNamespace(
        key="old",
        controller_port=8907,
        theater=SimpleNamespace(root=tmp_path / "old", db_port=6379, api_port=8908),
        report=lambda: calls.append("archive"),
        close=lambda: calls.append("close"),
    )
    fresh = SimpleNamespace(
        key="fresh",
        session="new",
        theater=SimpleNamespace(commit="abc"),
        launch=lambda: calls.append("launch"),
        close=lambda: None,
    )
    app = terminal_app(old, factory=lambda *args: fresh, allow_staged_reset=True)
    with TestClient(app, base_url="http://localhost") as client:
        assert client.post("/reset?start=false", headers={"x-demo-key": "old"}).status_code == 200
        assert calls == ["archive", "close"]
        assert app.state.live is fresh
        assert client.get("/connection").json()["key"] == "fresh"
