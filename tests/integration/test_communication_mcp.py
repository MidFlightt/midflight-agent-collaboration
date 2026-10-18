"""Independent MCP processes, exactly four tools, and restart recovery."""

import asyncio
import json
import sys
import uuid
from contextlib import AsyncExitStack, asynccontextmanager

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from midflight.communication.store import Store


@asynccontextmanager
async def connect(graph, port):
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "midflight.communication.mcp"],
        env={"MIDFLIGHT_PROJECT": graph, "MIDFLIGHT_DB_PORT": str(port)},
    )
    async with stdio_client(parameters) as (read, write), ClientSession(read, write) as client:
        await client.initialize()
        yield client


async def call(client, tool, **args):
    reply = await client.call_tool(tool, args)
    assert not reply.is_error, reply.content
    return json.loads(reply.content[0].text)


def test_real_stdio_processes_recover_objection_and_cursor(falkor_server):
    graph = "communication-mcp-" + uuid.uuid4().hex
    store = Store(graph, falkor_server.port)

    async def scenario():
        async with AsyncExitStack() as stack:
            a = await stack.enter_async_context(connect(graph, falkor_server.port))
            b = await stack.enter_async_context(connect(graph, falkor_server.port))
            assert {t.name for t in (await a.list_tools()).tools} == {
                "join",
                "send",
                "check_in",
                "object",
            }
            ja, jb = await asyncio.gather(
                call(a, "join", name="a", task="Billing", request_id="j", dependencies=["records"]),
                call(
                    b, "join", name="b", task="Delivery", request_id="j", dependencies=["records"]
                ),
            )
            sa, sb = ja["session_id"], jb["session_id"]
            publication = await call(
                a,
                "send",
                session_id=sa,
                kind="policy",
                body="Retain fee",
                source="Retain fee",
                request_id="p",
                topic="records",
            )
            objection = await call(
                b,
                "object",
                session_id=sb,
                publication_id=publication["event_id"],
                revision=1,
                problem="Historical refunds must not change",
                affects="saved records requirement",
                request_id="o",
            )
            assert objection["objection_id"]
            final = await call(b, "check_in", session_id=sb)
        async with connect(graph, falkor_server.port) as recovered:
            inbox = await call(recovered, "check_in", session_id=sb)
            assert inbox["cursor"] == final["cursor"] and not inbox["messages"]
            fresh = await call(recovered, "join", name="b", task="Delivery", request_id="fresh")
            assert fresh["updates"]["open_objections"][0]["id"] == objection["objection_id"]

    try:
        asyncio.run(scenario())
    finally:
        store.graph.delete()
        store.close()


def test_owner_publication_over_stdio_without_agree(falkor_server):
    from midflight.communication.service import Service

    graph = "published-mcp-" + uuid.uuid4().hex
    store = Store(graph, falkor_server.port)

    async def scenario():
        async with connect(graph, falkor_server.port) as owner:
            joined = await call(owner, "join", name="owner", task="Provide API", request_id="j")
            Service(store).configure_interfaces({"api": "owner"})
            published = await call(
                owner,
                "send",
                session_id=joined["session_id"],
                kind="interface",
                body="Return copied records",
                request_id="p",
                topic="api",
                expected_revision=0,
            )
        async with connect(graph, falkor_server.port) as consumer:
            joined = await call(
                consumer,
                "join",
                name="consumer",
                task="Use API",
                request_id="j",
                dependencies=["api"],
            )
            assert joined["updates"]["interfaces"][0]["id"] == published["event_id"]
            assert not Service(store).status().get("proposals", {})
            bad = await consumer.call_tool(
                "send",
                {
                    "session_id": joined["session_id"],
                    "kind": "interface",
                    "body": "Wrong owner",
                    "request_id": "bad",
                    "topic": "api",
                    "expected_revision": 1,
                },
            )
            assert bad.is_error and "Only the interface owner" in bad.content[0].text

    try:
        asyncio.run(scenario())
    finally:
        store.graph.delete()
        store.close()
