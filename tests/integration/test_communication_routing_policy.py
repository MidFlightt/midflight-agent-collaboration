"""Routing cannot be overridden; supersession never implies delivery or application."""

import uuid

import pytest

from midflight.communication.service import Service
from midflight.communication.store import Store


@pytest.fixture
def team(falkor_server):
    store = Store("routing-" + uuid.uuid4().hex, falkor_server.port)
    s = Service(store)
    ids = {
        n: s.join(n, n, "join", dependencies=d)["session_id"]
        for n, d in {"billing": ["revenue"], "delivery": ["policy"], "booking": []}.items()
    }
    s.send(
        ids["billing"],
        "dependency",
        "Revenue uses policy",
        "dep",
        topic="revenue",
        depends_on=["policy"],
    )
    yield s, ids
    store.graph.delete()
    store.close()


@pytest.mark.parametrize("kind", ["policy", "implementation", "message", "verification"])
@pytest.mark.parametrize("to", [["delivery"], ["booking"]])
def test_topic_updates_cannot_narrow_or_bypass_graph(team, kind, to):
    s, ids = team
    with pytest.raises(ValueError, match="all dependency subscribers"):
        s.send(
            ids["delivery"],
            kind,
            "change",
            "bad",
            topic="policy",
            to=to,
            source="human change" if kind == "policy" else "",
        )
    r = s.send(
        ids["delivery"],
        kind,
        "change",
        "ok",
        topic="policy",
        source="human change" if kind == "policy" else "",
    )
    assert r["recipients"] == ["billing", "delivery"]
    assert not s.check_in(ids["booking"])["messages"]
    direct = s.send(ids["delivery"], "question", "Direct question", "direct", to=["booking"])
    assert direct["recipients"] == ["booking"]


def test_supersession_exact_application_and_restart(team, falkor_server):
    s, ids = team
    before = s.status()["sessions"][ids["billing"]].copy()
    first = s.send(ids["delivery"], "policy", "400", "p1", topic="policy", source="400")
    second = s.send(
        ids["delivery"],
        "policy",
        "500 replaces 400",
        "p2",
        topic="policy",
        source="500",
        expected_revision=1,
    )
    assert s.status()["sessions"][ids["billing"]] == before
    falkor_server.kill_and_restart()
    recovered = Service(Store(s.store.graph.name, falkor_server.port))
    inbox = recovered.check_in(ids["billing"])
    assert [p["id"] for p in inbox["unapplied_policies"]] == [second["event_id"]]
    old, current = inbox["policy_history"]
    assert old["superseded_by"] == current["id"]
    assert not old["applied_report_ids"] and not old["previously_delivered"]
    assert not current["previously_delivered"]
    recovered.send(
        ids["billing"], "applied", "Historical work only", "old", reply_to=first["event_id"]
    )
    assert recovered.check_in(ids["billing"])["unapplied_policies"][0]["id"] == second["event_id"]
    applied = recovered.send(
        ids["billing"], "applied", "Current code tested", "new", reply_to=second["event_id"]
    )
    assert not applied["updates"]["unapplied_policies"]
    assert recovered.send(
        ids["billing"], "applied", "Current code tested", "new", reply_to=second["event_id"]
    )["duplicate"]
    fresh = recovered.join("billing", "new session", "fresh")["updates"]
    assert all(not p["previously_delivered"] for p in fresh["policy_history"])
    assert not fresh["unapplied_policies"]  # actor reports, independent session delivery
    assert not recovered.check_in(ids["booking"])["policy_history"]
    recovered.store.close()


def test_topic_replies_cannot_relabel_or_narrow(team):
    s, ids = team
    p = s.send(ids["delivery"], "policy", "fee", "p", topic="policy", source="fee")
    for to in (["billing"], ["booking"]):
        with pytest.raises(ValueError, match="cannot expand or narrow"):
            s.send(ids["delivery"], "applied", "done", str(to), reply_to=p["event_id"], to=to)
    with pytest.raises(ValueError, match="match its parent"):
        s.send(ids["delivery"], "message", "wrong", "wrong", topic="other", reply_to=p["event_id"])
    result = s.send(ids["delivery"], "applied", "done", "done", reply_to=p["event_id"])
    assert result["recipients"] == ["billing", "delivery"]
    assert s.status()["events"][-1]["topic"] == "policy"


def test_linked_topic_update_keeps_graph_audience(team):
    s, ids = team
    private = s.send(ids["delivery"], "message", "Private discussion", "private", to=["booking"])
    update = s.send(
        ids["delivery"],
        "implementation",
        "Public affected work",
        "linked",
        topic="policy",
        reply_to=private["event_id"],
    )
    assert update["recipients"] == ["billing", "delivery"]
