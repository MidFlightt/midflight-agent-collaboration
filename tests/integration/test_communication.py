"""Real FalkorDB tests; each test owns an isolated disposable graph."""

import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest

from midflight.communication.service import Service
from midflight.communication.store import Store


@pytest.fixture
def service(falkor_server):
    store = Store("communication-test-" + uuid.uuid4().hex, falkor_server.port)
    service = Service(store)
    yield service
    store.graph.delete()
    store.close()


def join(s, name, deps=None, key="join"):
    return s.join(name, name, key, dependencies=deps)["session_id"]


def test_routing_exact_revisions_retry_and_recovery(service):
    s = service
    a = join(s, "billing", ["records", "cancellation"])
    b = join(s, "delivery", ["records", "cancellation"])
    c = join(s, "booking", ["booking-request"])
    d = join(s, "notifications", ["confirmation"])
    policy = s.send(
        b,
        "policy",
        "Retain 400 cents",
        "fee",
        topic="cancellation",
        source="Keep a four-credit cancellation fee",
    )
    assert policy["recipients"] == ["billing", "delivery"]
    for sid in (c, d):
        assert s.check_in(sid)["messages"] == []
        assert s.check_in(sid)["unapplied_policies"] == []
    # A new independent connection/process recovers all state from the graph.
    recovered_store = Store(
        s.store.graph.name, s.store.client.connection.connection_pool.connection_kwargs["port"]
    )
    recovered = Service(recovered_store)
    fresh = join(recovered, "billing", key="new-session")
    assert fresh != a
    assert recovered.check_in(fresh)["unapplied_policies"][0]["id"] == policy["event_id"]
    assert recovered.check_in(a)["messages"][-1]["id"] == policy["event_id"]
    assert recovered.check_in(a)["messages"] == []
    assert recovered.check_in(a, after=0)["messages"]
    with pytest.raises(ValueError, match="received cursor"):
        recovered.check_in(a, after=999)
    recovered_store.close()


def test_graph_transitive_and_replaced_dependencies(service):
    s = service
    a = join(s, "a", ["report"])
    b = join(s, "b", ["records"])
    s.send(a, "dependency", "Report uses records", "dep", topic="report", depends_on=["records"])
    result = s.send(
        b, "policy", "Change record semantics", "change", topic="records", source="Change records"
    )
    assert result["recipients"] == ["a", "b"]
    s.join("a", "a", "unsubscribe", a, [])
    result = s.send(b, "message", "Next record update", "next", topic="records")
    assert result["recipients"] == ["b"]
    with pytest.raises(ValueError, match="cycle"):
        s.send(b, "dependency", "Cycle", "cycle", topic="records", depends_on=["report"])


def test_concurrent_requests_commit_exactly_once(service):
    s = service
    a = join(s, "a", ["topic"])
    b = join(s, "b", ["topic"])

    def send(i):
        store = Store(
            s.store.graph.name, s.store.client.connection.connection_pool.connection_kwargs["port"]
        )
        try:
            return Service(store).send(a, "message", f"event {i % 8}", f"m{i % 8}", to=["b"])
        finally:
            store.close()

    with ThreadPoolExecutor(8) as pool:
        results = list(pool.map(send, range(24)))
    assert len(s.status()["events"]) == 8
    assert sum(not r["duplicate"] for r in results) == 8
    assert len(s.check_in(b)["messages"]) == 8


def test_independent_cursors_pagination_and_lost_response(service):
    s = service
    a = join(s, "a")
    b = join(s, "b")
    b2 = join(s, "b", key="second")
    for i in range(55):
        s.send(a, "message", str(i), str(i), to=["b"])
    first = s.check_in(b)
    assert first["more"] and len(first["messages"]) == 50
    assert len(s.check_in(b2)["messages"]) == 50
    assert len(s.check_in(b, after=0)["messages"]) == 50
    assert len(s.check_in(b)["messages"]) == 5
    assert len(s.check_in(b2)["messages"]) == 5


def test_no_broadcast_or_implicit_authority(service):
    s = service
    a = join(s, "a")
    b = join(s, "b")
    with pytest.raises(ValueError, match="no broadcast"):
        s.send(a, "message", "raw direction", "bad")
    s.send(a, "implementation", "Code exists", "code", to=["b"])
    assert s.check_in(b)["messages"][0]["kind"] == "implementation"
    with pytest.raises(ValueError, match="Unknown message kind"):
        s.send(a, "proposal", "Removed", "removed", topic="api")
    assert not hasattr(s, "agree")


def test_database_crash_preserves_receipts_cursors_and_pending_work(service, falkor_server):
    s = service
    a = join(s, "a", ["policy"])
    b = join(s, "b", ["policy"])
    event = s.send(a, "policy", "Four credits", "fee", topic="policy", source="Keep four credits")
    delivered = s.check_in(b)
    falkor_server.kill_and_restart()
    recovered = Service(Store(s.store.graph.name, falkor_server.port))
    assert recovered.check_in(b)["messages"] == []
    assert recovered.check_in(b)["unapplied_policies"][0]["id"] == event["event_id"]
    assert recovered.check_in(b, after=0)["messages"] == delivered["messages"]
    assert recovered.send(
        a, "policy", "Four credits", "fee", topic="policy", source="Keep four credits"
    )["duplicate"]
    recovered.store.close()


def test_policy_and_application_cannot_leak_to_unrelated_agents(service):
    s = service
    a = join(s, "billing", ["cancellation"])
    b = join(s, "delivery", ["cancellation"])
    c = join(s, "booking", ["booking-request"])
    with pytest.raises(ValueError, match="dependency subscribers"):
        s.send(
            b,
            "policy",
            "Fee",
            "bad",
            topic="cancellation",
            source="Keep four credits",
            to=["booking"],
        )
    policy = s.send(b, "policy", "Fee", "fee", topic="cancellation", source="Keep four credits")
    with pytest.raises(ValueError, match="cannot expand"):
        s.send(
            b,
            "applied",
            "Code changed",
            "leak",
            reply_to=policy["event_id"],
            to=["billing", "booking"],
        )
    assert len(s.status()["events"]) == 1
    s.send(b, "applied", "Code changed", "fixed", reply_to=policy["event_id"])
    assert s.check_in(c)["messages"] == []
    assert s.check_in(a)["unapplied_policies"]
    assert not s.check_in(b)["unapplied_policies"]
