"""Owner publication replaces routine mutual acceptance; all tests use real FalkorDB."""

import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest

from midflight.communication.service import Service
from midflight.communication.store import Store


@pytest.fixture
def team(falkor_server):
    store = Store("published-" + uuid.uuid4().hex, falkor_server.port)
    s = Service(store)
    sessions = {
        name: s.join(name, name, "join", dependencies=deps)["session_id"]
        for name, deps in {
            "provider": ["records"],
            "consumer": ["records"],
            "unrelated": [],
        }.items()
    }
    s.configure_interfaces({"records": "provider"})
    yield s, sessions
    store.graph.delete()
    store.close()


def publish(s, sid, key="publish", expected=0, body="Return ID-keyed records"):
    return s.send(sid, "interface", body, key, topic="records", expected_revision=expected)


def test_publication_default_without_agreement_and_independent_delivery(team):
    s, ids = team
    initial = publish(s, ids["provider"])
    assert not s.status().get("proposals", {})
    assert s.status()["interfaces"]["records"]["id"] == initial["event_id"]
    assert "records" not in s.status()["sessions"][ids["consumer"]].get(
        "delivered_interface_revisions", {}
    )
    inbox = s.check_in(ids["consumer"])
    assert inbox["interfaces"][0]["revision"] == 1
    assert inbox["interfaces"][0]["previously_delivered_revision"] == 0
    assert s.check_in(ids["consumer"])["interfaces"][0]["previously_delivered_revision"] == 1
    assert not s.check_in(ids["unrelated"])["interfaces"]
    fresh = s.join("consumer", "new chat", "new")["updates"]
    assert fresh["interfaces"][0]["previously_delivered_revision"] == 0
    assert publish(s, ids["provider"])["duplicate"]
    assert len(s.status()["events"]) == 1


def test_consumers_cannot_win_a_race_or_silently_take_ownership(team):
    s, ids = team

    def attempt(name):
        try:
            return publish(s, ids[name], key=name)
        except ValueError as error:
            return str(error)

    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(attempt, ["consumer", "provider"]))
    assert "Only the interface owner" in results[0]
    assert results[1]["revision"] == 1
    assert s.status()["owners"]["records"]["name"] == "provider"
    with pytest.raises(ValueError, match="setup cannot replace"):
        s.configure_interfaces({"records": "consumer"})
    with pytest.raises(ValueError, match="No assigned owner"):
        s.send(ids["consumer"], "interface", "Guess", "guess", topic="unknown")


def test_concurrent_owner_revisions_cannot_overwrite_each_other(team):
    s, ids = team
    publish(s, ids["provider"])

    def attempt(i):
        try:
            return publish(s, ids["provider"], str(i), 1, f"Revision from writer {i}")
        except ValueError:
            return None

    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(attempt, range(2)))
    assert sum(r is not None for r in results) == 1
    assert s.status()["interfaces"]["records"]["revision"] == 2


def test_objection_survives_publication_read_and_restart_until_author_resolves(team):
    s, ids = team
    p = publish(s, ids["provider"])
    objection = s.object(
        ids["consumer"],
        p["event_id"],
        1,
        "Existing caller expects list",
        "records dependency",
        "object",
    )
    publish(s, ids["provider"], "v2", 1, "Return list")
    assert s.check_in(ids["provider"])["open_objections"][0]["publication_revision"] == 1
    with pytest.raises(ValueError, match="Only the objection author"):
        s.send(
            ids["provider"],
            "resolve",
            "I changed it",
            "silence",
            reply_to=objection["objection_id"],
        )
    restarted = Service(
        Store(
            s.store.graph.name, s.store.client.connection.connection_pool.connection_kwargs["port"]
        )
    )
    try:
        assert restarted.check_in(ids["consumer"])["open_objections"]
        restarted.send(
            ids["consumer"],
            "resolve",
            "Combined test passes with revision 2",
            "resolved",
            reply_to=objection["objection_id"],
        )
        assert not restarted.check_in(ids["provider"])["open_objections"]
        assert not restarted.check_in(ids["unrelated"])["messages"]
    finally:
        restarted.store.close()


def test_owner_transfer_preserves_interface_and_has_its_own_revision(team):
    s, ids = team
    p = publish(s, ids["provider"])
    transferred = s.send(
        ids["provider"],
        "transfer",
        "Consumer maintains the API now",
        "transfer",
        topic="records",
        new_owner="consumer",
        expected_revision=1,
    )
    assert transferred["revision"] == 2
    assert s.status()["interfaces"]["records"]["id"] == p["event_id"]
    assert s.check_in(ids["consumer"])["interfaces"][0]["owner"] == "consumer"
    with pytest.raises(ValueError, match="Only the interface owner"):
        publish(s, ids["provider"], "old", 1, "Wrong owner")
    assert publish(s, ids["consumer"], "new", 1, "New implementation")["revision"] == 2
    assert s.send(
        ids["provider"],
        "transfer",
        "Consumer maintains the API now",
        "transfer",
        topic="records",
        new_owner="consumer",
        expected_revision=1,
    )["duplicate"]


def test_late_subscriber_gets_current_contract_and_can_object(team):
    s, ids = team
    p = publish(s, ids["provider"])
    joined = s.join("late", "Consumer", "late", dependencies=["records"])
    assert joined["updates"]["interfaces"][0]["id"] == p["event_id"]
    assert joined["updates"]["interfaces"][0]["previously_delivered_revision"] == 0
    s.object(
        joined["session_id"],
        p["event_id"],
        1,
        "Concrete incompatibility",
        "records dependency",
        "object",
    )
    assert s.check_in(ids["provider"])["open_objections"]


def test_human_change_does_not_revise_interface_or_advance_idle_session(team):
    s, ids = team
    publish(s, ids["provider"])
    before = s.status()["sessions"][ids["consumer"]].copy()
    s.send(
        ids["provider"],
        "policy",
        "Use saved fee",
        "fee",
        topic="records",
        source="Keep four credits",
    )
    assert s.status()["interfaces"]["records"]["revision"] == 1
    assert s.status()["sessions"][ids["consumer"]] == before
    assert s.check_in(ids["consumer"])["unapplied_policies"]


def test_discussion_and_tests_do_not_publish_or_resolve(team):
    s, ids = team
    p = publish(s, ids["provider"])
    objection = s.object(ids["consumer"], p["event_id"], 1, "Mismatch", "records", "o")
    s.send(ids["provider"], "verification", "Tests pass", "tests", topic="records")
    s.send(ids["provider"], "message", "Consider an alternative", "alternative", topic="records")
    assert s.status()["interfaces"]["records"]["id"] == p["event_id"]
    assert s.status()["objections"][str(objection["objection_id"])]["state"] == "open"


def test_reply_link_cannot_narrow_interface_delivery(team):
    s, ids = team
    note = s.send(ids["unrelated"], "message", "Private note", "note", to=["provider"])
    p = s.send(
        ids["provider"],
        "interface",
        "Return mapping",
        "publish",
        topic="records",
        reply_to=note["event_id"],
    )
    assert p["recipients"] == ["consumer", "provider"]
    assert s.check_in(ids["consumer"])["interfaces"][0]["id"] == p["event_id"]


def test_transfer_routes_outstanding_objections_to_new_owner_without_subscription(team):
    s, ids = team
    p = publish(s, ids["provider"])
    o = s.object(ids["consumer"], p["event_id"], 1, "Mismatch", "records dependency", "o")
    s.send(
        ids["provider"],
        "transfer",
        "New maintainer",
        "transfer",
        topic="records",
        new_owner="unrelated",
        expected_revision=1,
    )
    assert s.check_in(ids["unrelated"])["open_objections"][0]["id"] == o["objection_id"]
    s.send(ids["unrelated"], "message", "Here is a fix", "fix", reply_to=o["objection_id"])
    s.send(ids["consumer"], "resolve", "Fix tested", "resolve", reply_to=o["objection_id"])
    assert s.check_in(ids["unrelated"])["messages"][-1]["kind"] == "resolve"


def test_database_crash_preserves_publication_objection_and_delivery_metadata(team, falkor_server):
    s, ids = team
    p = publish(s, ids["provider"])
    s.object(ids["consumer"], p["event_id"], 1, "Mismatch", "records dependency", "o")
    falkor_server.kill_and_restart()
    recovered = Service(Store(s.store.graph.name, falkor_server.port))
    try:
        inbox = recovered.check_in(ids["consumer"])
        assert inbox["interfaces"][0]["previously_delivered_revision"] == 1
        assert inbox["open_objections"][0]["reply_to"] == p["event_id"]
        assert publish(recovered, ids["provider"])["duplicate"]
    finally:
        recovered.store.close()
