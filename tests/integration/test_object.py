"""Exact objections remain durable signals across revisions, retries and restarts."""

import copy
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest

from midflight.communication.service import Service
from midflight.communication.store import Store


@pytest.fixture
def team(falkor_server):
    store = Store("objects-" + uuid.uuid4().hex, falkor_server.port)
    s = Service(store)
    ids = {
        n: s.join(n, n, "join", dependencies=d)["session_id"]
        for n, d in {
            "delivery": ["records", "fee"],
            "billing": ["revenue"],
            "booking": ["records"],
            "notifications": [],
        }.items()
    }
    s.send(
        ids["billing"],
        "dependency",
        "Revenue depends on records and fee",
        "deps",
        topic="revenue",
        depends_on=["records", "fee"],
    )
    s.configure_interfaces({"records": "delivery"})
    yield s, ids
    store.graph.delete()
    store.close()


@pytest.mark.parametrize(
    "kind,topic,recipients",
    [
        ("interface", "records", ["billing", "booking", "delivery"]),
        ("policy", "fee", ["billing", "delivery"]),
    ],
)
def test_exact_objection_optional_solution_routing_and_resolution(team, kind, topic, recipients):
    s, ids = team
    pub = s.send(
        ids["delivery"],
        kind,
        "Published",
        "pub",
        topic=topic,
        source="Human direction" if kind == "policy" else "",
    )
    before = copy.deepcopy(s.status()["sessions"][ids["booking"]])
    o = s.object(
        ids["billing"],
        pub["event_id"],
        1,
        "Breaks historical refunds",
        "Revenue must use saved amounts",
        "o",
    )
    assert o["recipients"] == recipients
    assert s.status()["sessions"][ids["booking"]] == before
    record = s.status()["objections"][str(o["objection_id"])]
    assert record["publication_revision"] == 1 and not record["alternative"]
    assert s.object(
        ids["billing"],
        pub["event_id"],
        1,
        "Breaks historical refunds",
        "Revenue must use saved amounts",
        "o",
    )["duplicate"]
    with pytest.raises(ValueError, match="different input"):
        s.object(ids["billing"], pub["event_id"], 1, "Different", "Saved amounts", "o")
    with pytest.raises(ValueError, match="wrong exact revision"):
        s.object(ids["billing"], pub["event_id"], 2, "Problem", "Requirement", "wrong")
    with pytest.raises(ValueError, match="not relevant"):
        s.object(ids["notifications"], pub["event_id"], 1, "Problem", "Requirement", "leak")
    with pytest.raises(ValueError, match="affected requirement"):
        s.object(ids["billing"], pub["event_id"], 1, "Problem", "", "missing")
    with pytest.raises(ValueError, match="Only the objection author"):
        s.send(ids["delivery"], "resolve", "I fixed it", "bad", reply_to=o["objection_id"])
    s.send(
        ids["delivery"],
        kind,
        "Revision 2",
        "rev2",
        topic=topic,
        expected_revision=1,
        source="New human direction" if kind == "policy" else "",
    )
    s.send(ids["delivery"], "verification", "Tests pass", "test", topic=topic)
    assert s.check_in(ids["billing"])["open_objections"][0]["publication_revision"] == 1
    resolved = s.send(
        ids["billing"],
        "resolve",
        "Verified saved amounts retained in revision 2",
        "resolve",
        reply_to=o["objection_id"],
    )
    assert resolved["recipients"] == recipients
    assert not s.check_in(ids["billing"])["open_objections"]
    assert s.send(
        ids["billing"],
        "resolve",
        "Verified saved amounts retained in revision 2",
        "resolve",
        reply_to=o["objection_id"],
    )["duplicate"]
    assert s.status()["objections"][str(o["objection_id"])]["resolution_id"] == resolved["event_id"]


def test_concurrent_revision_and_duplicate_objection_recover(team, falkor_server):
    s, ids = team
    pub = s.send(ids["delivery"], "policy", "First", "p", topic="fee", source="First")

    def write(i):
        if i < 4:
            return s.object(
                ids["billing"], pub["event_id"], 1, "Preserve history", "Saved refunds", "same"
            )
        return s.send(
            ids["delivery"],
            "policy",
            "Second",
            "p2",
            topic="fee",
            source="Second",
            expected_revision=1,
        )

    with ThreadPoolExecutor(5) as pool:
        results = list(pool.map(write, range(5)))
    assert len({r["objection_id"] for r in results[:4]}) == 1
    assert sum(not r["duplicate"] for r in results[:4]) == 1
    objection_id = results[0]["objection_id"]
    falkor_server.kill_and_restart()
    recovered = Service(Store(s.store.graph.name, falkor_server.port))
    try:
        inbox = recovered.check_in(ids["billing"])
        assert inbox["open_objections"][0]["id"] == objection_id
        assert inbox["open_objections"][0]["publication_revision"] == 1
        assert inbox["unapplied_policies"][0]["revision"] == 2
        fresh = recovered.join("billing", "fresh chat", "fresh")["updates"]
        assert fresh["open_objections"][0]["id"] == objection_id
        assert recovered.object(
            ids["billing"], pub["event_id"], 1, "Preserve history", "Saved refunds", "same"
        )["duplicate"]
        assert not recovered.check_in(ids["notifications"])["messages"]
    finally:
        recovered.store.close()


def test_historical_agreements_are_preserved_but_not_actionable(team):
    s, ids = team
    history = {
        "42": {
            "state": "agreed",
            "participants": ["billing", "delivery"],
            "revision": 1,
            "body": "Old contract",
        }
    }
    s._mutate(lambda state, revision: state.update(proposals=copy.deepcopy(history)))
    inbox = s.check_in(ids["billing"])
    assert "pending_proposals" not in inbox and "agreements" not in inbox
    assert s.status()["proposals"] == history
    assert not hasattr(s, "agree")
    for kind in ["proposal", "objection"]:
        with pytest.raises(ValueError, match="Unknown message kind"):
            s.send(ids["billing"], kind, "Removed path", kind, topic="records")


def test_integration_report_keeps_open_objections_without_advancing_sessions(team, tmp_path):
    import hashlib
    import json
    from types import SimpleNamespace

    from midflight.communication.harness import CommunicationTheater
    from midflight.communication.validate import NAMES, coordination_objections

    s, ids = team
    pub = s.send(ids["delivery"], "policy", "Fee", "p", topic="fee", source="Fee")
    o = s.object(ids["billing"], pub["event_id"], 1, "Historical refunds", "Saved amounts", "o")
    (tmp_path / "run.json").write_text(
        json.dumps(
            {
                "graph": s.store.graph.name,
                "db_port": s.store.client.connection.connection_pool.connection_kwargs["port"],
            }
        )
    )
    before = copy.deepcopy(s.status()["sessions"])
    assert coordination_objections(tmp_path)["open_objections"][0]["id"] == o["objection_id"]
    hashes = {}
    for n in NAMES:
        (tmp_path / n).mkdir()
        (tmp_path / n / (n + ".py")).write_text("# Tested bytes\n")
        hashes[n] = hashlib.sha256(b"# Tested bytes\n").hexdigest()
    (tmp_path / "integration.json").write_text(json.dumps({"success": True, "hashes": hashes}))
    live = CommunicationTheater.__new__(CommunicationTheater)
    live.theater = SimpleNamespace(root=tmp_path, project=s.store.graph.name)
    live.session = "test"
    live.service = s
    report = live.report()
    assert report["integration"]["success"]  # Test result is not an approval gate.
    assert report["integration"]["current_open_objections"][0]["id"] == o["objection_id"]
    assert s.status()["sessions"] == before
    assert s.status()["objections"][str(o["objection_id"])]["state"] == "open"


def test_legacy_objection_remains_visible_and_author_resolvable(team):
    s, ids = team
    pub = s.send(ids["delivery"], "interface", "Mapping", "p", topic="records")

    def old_writer(state, revision):
        event = s._event(
            state,
            "billing",
            "objection",
            "Legacy caller mismatch",
            ["billing", "delivery"],
            topic="records",
            reply_to=pub["event_id"],
            revision=0,
            source="",
            depends_on=[],
        )
        state["objections"][str(event["id"])] = event | {
            "interface_revision": 1,
            "state": "open",
            "resolution_id": None,
        }
        return event["id"]

    oid = s._mutate(old_writer)
    legacy = copy.deepcopy(s.status()["objections"][str(oid)])
    assert s.check_in(ids["billing"])["open_objections"][0] == legacy
    assert "affects" not in legacy  # Never invent missing history.
    s.send(
        ids["billing"],
        "resolve",
        "Adapted caller and verified saved refunds",
        "resolve",
        reply_to=oid,
    )
    final = s.status()["objections"][str(oid)]
    assert final["state"] == "resolved"
    assert {k: v for k, v in final.items() if k not in {"state", "resolution_id"}} == {
        k: v for k, v in legacy.items() if k not in {"state", "resolution_id"}
    }
