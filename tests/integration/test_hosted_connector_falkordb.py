"""Hosted projects, sign-in records and coordination persist in real FalkorDB.

Opt-in like the other database tests: `uv run --extra falkordb pytest --falkordb`.
"""

import time
import uuid

from midflight.communication.hosted import falkor_backend
from midflight.ports import GitHubAccount


def test_projects_sessions_and_tokens_survive_a_restart(falkor_server):
    prefix = "hostedtest_" + uuid.uuid4().hex + "_"
    registry, services = falkor_backend("127.0.0.1", falkor_server.port, prefix)
    lead = registry.sign_in(GitHubAccount(101, "somesh")).id
    mate = registry.sign_in(GitHubAccount(202, "frederik")).id
    project = registry.create_project(lead, "Food app")
    pid = project["project_id"]
    registry.join_project(mate, project["join_code"])

    registry.bind_agent(lead, pid, "orders")
    joined = services(pid).join("orders", "Orders", "j", dependencies=["order-record"])
    registry.record_session(lead, pid, "orders", joined["session_id"])
    registry.bind_agent(mate, pid, "payments")
    services(pid).join("payments", "Payments", "j", dependencies=["order-record"])
    published = services(pid).send(
        joined["session_id"], "interface", "{id}", "p", topic="order-record", expected_revision=0
    )
    assert published["claimed_ownership"] and published["recipients"] == ["orders", "payments"]

    registry.put_auth("access", "hash-1", {"subject": lead}, time.time() + 60)
    registry.put_auth("access", "hash-old", {"subject": lead}, time.time() - 1)

    # A new Lambda instance: fresh connections, same data.
    again, services_again = falkor_backend("127.0.0.1", falkor_server.port, prefix)
    assert again.session(lead, joined["session_id"]) == (pid, "orders")
    assert again.get_auth("access", "hash-1") == {"subject": lead}
    assert again.get_auth("access", "hash-old") is None
    again.delete_auth("access", "hash-1")
    assert again.get_auth("access", "hash-1") is None
    state = services_again(pid).status()
    assert state["owners"]["order-record"] == {"name": "orders", "revision": 1}
    [view] = again.projects_of(mate)
    assert view["agents"] == {"orders": "somesh", "payments": "frederik"}

    for store in (registry.store, *(s.store for s in services.services.values())):
        store.graph.delete()
        store.close()
    registry.auth.graph.delete()
