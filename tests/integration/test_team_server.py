"""Team onboarding end to end on FalkorDB: two people, separately signed in, one project.

Alice (lead, backend) and Bob (frontend) each register their own client and sign in, the
way Claude Code or Codex does on their own computer. The dev login stands in for GitHub
here (it only runs on 127.0.0.1); everything after sign-in is the real team server.
"""

from __future__ import annotations

import re
import threading
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager

import pytest
import uvicorn
from integration.test_hosted_server_http import call, sign_in

from midflight.config import Settings
from midflight.main import create_server

pytestmark = pytest.mark.anyio

REFUSED = "Midflight refused this"


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@contextmanager
def team_server(port: int, falkor_port: int, graph: str) -> Iterator[str]:
    url = f"http://127.0.0.1:{port}"
    settings = Settings(
        public_url=url,
        dev_login=True,
        store_backend="falkordb",
        falkor_port=falkor_port,
        falkor_graph=graph,
    )
    app = create_server(settings).app
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 15
    while not server.started:
        assert time.monotonic() < deadline, "server didn't start"
        time.sleep(0.05)
    try:
        yield url
    finally:
        server.should_exit = True
        thread.join(timeout=15)


def free_port() -> int:
    import socket

    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def plan(currency: bool = False) -> dict:
    fields = {"total_cents": "integer"} | ({"currency": "string"} if currency else {})
    return {
        "requirements": [
            {"id": "orders", "description": "Show a customer's orders"},
        ],
        "tasks": [
            {"id": "api", "title": "Orders API", "owner": "alice", "provides": ["order"]},
            {"id": "page", "title": "Orders page", "owner": "bob", "consumes": ["order"]},
        ],
        "contracts": [
            {"id": "order", "provider_task": "api", "consumer_tasks": ["page"], "fields": fields}
        ],
    }


async def test_two_people_share_one_project_with_separate_permissions(falkor_server) -> None:
    port, graph = free_port(), "team_" + uuid.uuid4().hex
    with team_server(port, falkor_server.port, graph) as url:
        alice = sign_in(url, "alice")["access_token"]
        bob = sign_in(url, "bob")["access_token"]
        assert alice != bob

        created = await call(url, alice, "create_project", repository="acme/shop")
        code = re.search(r"Join code: (MF-\S+)", created).group(1)  # type: ignore[union-attr]
        joined = await call(url, bob, "join_project", join_code=code)
        assert "Lead: alice" in joined

        proposed = await call(url, alice, "propose_plan", **plan())
        assert "Proposed plan v1" in proposed, proposed
        approved = await call(url, alice, "approve_plan", version=1, reason="Alice reviewed")
        assert "Plan v1 is approved" in approved

        # Bob sees the same approved plan, and his own task and contract.
        assert "you are agent" in await call(url, bob, "my_projects")
        status = await call(url, bob, "project_status")
        assert "Plan v1" in status and "page Orders page (bob)" in status
        assert "Join code" not in status  # only the lead sees the join code
        assert "total_cents" in await call(url, bob, "check_in", task_id="page")

        # Lead-only actions are refused for Bob, and change nothing.
        for tool, args in [
            ("propose_plan", plan(currency=True)),
            ("approve_plan", {"version": 1, "reason": "Bob approves"}),
            ("assign_task", {"task_id": "api", "member": "bob"}),
            ("rotate_join_code", {}),
            ("remove_member", {"member": "alice"}),
        ]:
            reply = await call(url, bob, tool, **args)
            assert REFUSED in reply and "lead" in reply, (tool, reply)
        assert "Plan v1" in await call(url, alice, "project_status")

    # Restart against the same graph: sign-ins and the plan survive, and a change made
    # after the restart reaches Bob at his next check-in.
    with team_server(port, falkor_server.port, graph) as url:
        assert "Plan v1" in await call(url, bob, "project_status")
        await call(url, alice, "propose_plan", **plan(currency=True))
        await call(url, alice, "approve_plan", version=2, reason="Prices need a currency")
        reply = await call(url, bob, "check_in", task_id="page")
        assert "currency" in reply and "D-" in reply, reply
