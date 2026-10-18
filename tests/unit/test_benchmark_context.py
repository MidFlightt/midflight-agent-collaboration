import asyncio
import copy
from types import SimpleNamespace

from mcp.types import CallToolResult, TextContent

from experiment.communication.context import CompactResponses, decode, dumps, encode


def fixture():
    policy = {"id": 7, "revision": 2, "body": "Exact source with Unicode æ and policy. " * 80}
    old = {"id": 5, "revision": 1, "body": "Earlier conflicting policy. " * 80}
    objection = {
        "id": 9,
        "publication_id": 5,
        "publication_revision": 1,
        "author": "t4",
        "state": "open",
        "affects": "R-5",
        "body": "Concrete problem",
    }
    return {
        "cursor": 9,
        "more": True,
        "messages": [policy, objection],
        "policy_history": [old | {"superseded_by": 7}, policy],
        "unapplied_policies": [policy],
        "interfaces": [policy],
        "open_objections": [objection],
        "questions": [],
        "recipients": ["t4"],
    }


def test_lossless_self_contained_history_objections_pagination():
    original = fixture()
    before = copy.deepcopy(original)
    packed = encode(original)
    assert len(dumps(packed)) < len(dumps(original))
    assert decode(packed) == before == original
    # New instance/process, lost previous context, retry: no cached state needed.
    assert decode(encode(original)) == original
    updated = copy.deepcopy(original)
    updated["open_objections"][0]["state"] = "resolved"
    updated["open_objections"][0]["resolution_id"] = 10
    assert decode(encode(updated)) == updated
    assert decode(packed)["open_objections"][0]["state"] == "open"


def test_literal_reference_shapes_are_preserved():
    original = fixture() | {"peer_data": [{"$text": "t0"}, {"$literal": ["anything"]}]}
    assert decode(encode(original)) == original
    assert encode({"more": False, "messages": []}) == {"more": False, "messages": []}


def test_middleware_preserves_errors_schemas_and_full_results():
    original = fixture()
    result = CallToolResult(
        content=[TextContent(type="text", text=dumps(original))], structured_content=original
    )

    async def apply(result, method="tools/call"):
        async def next_handler(ctx):
            return result

        return await CompactResponses()(SimpleNamespace(method=method), next_handler)

    packed = asyncio.run(apply(result))
    import json

    assert decode(json.loads(packed.content[0].text)) == original
    assert decode(packed.structured_content) == original
    assert asyncio.run(apply(result, "tools/list")) is result
    error = result.model_copy(update={"is_error": True})
    assert asyncio.run(apply(error)) is error
    distinct = result.model_copy(update={"structured_content": {"other": "evidence"}})
    assert asyncio.run(apply(distinct)) is distinct


def test_actual_stdio_transport_keeps_four_tools_and_self_contained_response(tmp_path):
    import json
    import sys
    from pathlib import Path

    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    original = fixture() | {"agent": "t4", "session_id": "offline-test"}
    for event in original["messages"]:
        event.setdefault("author", "t1")
        event.setdefault("kind", "policy")
    payload = tmp_path / "response.json"
    payload.write_text(json.dumps(original))
    script = tmp_path / "server.py"
    script.write_text("""import json,sys
from pathlib import Path
from experiment.communication.context import CompactResponses
from midflight.communication.mcp import build_server
class Fake:
    def __getattr__(self, name):
        def invoke(*args):
            return json.loads(Path(sys.argv[1]).read_text())
        invoke.__name__ = name
        return invoke
server = build_server(Fake(), remote=True)
middleware = CompactResponses()
server.middleware.append(middleware)
server.run("stdio")
""")

    async def smoke():
        params = StdioServerParameters(
            command=sys.executable,
            args=[str(script), str(payload)],
            env={"PYTHONPATH": str(Path(__file__).resolve().parents[2])},
        )
        async with stdio_client(params) as (read, write):  # noqa: SIM117
            async with ClientSession(read, write) as session:
                await session.initialize()
                listing = await session.list_tools()
                assert {t.name for t in listing.tools} == {"join", "send", "check_in", "object"}
                result = await session.call_tool("check_in", {"session_id": "offline-test"})
                assert not result.is_error
                wire = json.loads(result.content[0].text)
                assert wire["encoding"] == "midflight-text-table-v1"
                expanded = decode(wire)
                assert {k: expanded[k] for k in original} == original
                assert "activity" in expanded

    asyncio.run(smoke())
