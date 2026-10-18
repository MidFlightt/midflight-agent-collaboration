"""Operator-run live transport checks. Use a dedicated verification project's credentials."""

import argparse
import asyncio
import json
import sys
import uuid
from contextlib import AsyncExitStack, asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


@asynccontextmanager
async def connect(url, token_file):
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "midflight.communication.mcp"],
        env={"MIDFLIGHT_URL": url, "MIDFLIGHT_TOKEN_FILE": str(token_file.resolve())},
    )
    async with stdio_client(params) as (read, write), ClientSession(read, write) as client:
        await client.initialize()
        yield client


async def call(client, tool, **args):
    response = await client.call_tool(tool, args)
    if response.is_error:
        raise AssertionError(str(response.content))
    return json.loads(response.content[0].text)


async def verify(url, credentials):
    run = uuid.uuid4().hex
    topic = "operator-smoke-" + run
    checks, sessions = [], {}
    with httpx.Client(timeout=40) as http:
        assert http.get(url + "/healthz").status_code == 200
        assert (
            http.post(
                url + "/v1/tools", json={"operation": "check_in", "session_id": "unknown"}
            ).status_code
            == 401
        )
    checks.append("HTTPS health and unauthenticated rejection")
    async with AsyncExitStack() as stack:
        clients = {
            name: await stack.enter_async_context(connect(url, credentials / (name + ".token")))
            for name in ("billing", "delivery", "booking", "notifications")
        }
        for name, client in clients.items():
            assert {t.name for t in (await client.list_tools()).tools} == {
                "join",
                "send",
                "check_in",
                "object",
            }
            joined = await call(
                client,
                "join",
                name=name,
                task="Operator transport verification",
                request_id=run + "-join",
                dependencies=([topic] if name in ("billing", "delivery") else []),
            )
            sessions[name] = joined["session_id"]
        checks.append("Four independent MCP processes expose exactly four tools")
        a, b = clients["billing"], clients["delivery"]
        second = await call(
            a,
            "join",
            name="billing",
            task="Operator independent cursor test",
            request_id=run + "-second",
        )
        args = dict(
            session_id=sessions["delivery"],
            kind="policy",
            topic=topic,
            body="Operator fixture: retain four credits",
            source="Operator transport test",
            request_id=run + "-policy",
            expected_revision=0,
        )
        sent = await call(b, "send", **args)
        assert sent["recipients"] == ["billing", "delivery"]
        duplicate = await call(b, "send", **args)
        assert duplicate["duplicate"] and duplicate["event_id"] == sent["event_id"]
        checks.append("Exact retry returns the original policy event")
        updated = await call(
            b,
            "send",
            **(
                args
                | {
                    "body": "Operator fixture: retain five credits",
                    "expected_revision": 1,
                    "request_id": run + "-new-policy",
                }
            ),
        )
        inbox = await call(a, "check_in", session_id=sessions["billing"])
        current = [p for p in inbox["unapplied_policies"] if p["topic"] == topic]
        assert [p["id"] for p in current] == [updated["event_id"]]
        old = next(p for p in inbox["policy_history"] if p["id"] == sent["event_id"])
        assert old["superseded_by"] == updated["event_id"] and not old["applied_report_ids"]
        for name in ("booking", "notifications"):
            unrelated = await call(clients[name], "check_in", session_id=sessions[name])
            assert all(m.get("topic") != topic for m in unrelated["messages"])
            assert all(p["topic"] != topic for p in unrelated["policy_history"])
        checks.append(
            "Fee routing reaches Billing/Delivery only; supersession preserves unapplied history"
        )
        obj = await call(
            a,
            "object",
            session_id=sessions["billing"],
            publication_id=updated["event_id"],
            revision=2,
            problem="Operator fixture: historical refunds must remain unchanged",
            affects="Operator test of historical record dependency",
            request_id=run + "-object",
        )
        assert obj["recipients"] == ["billing", "delivery"]
        rejected = await b.call_tool(
            "send",
            dict(
                session_id=sessions["delivery"],
                kind="resolve",
                body="Operator negative authorization test",
                request_id=run + "-wrong-resolve",
                reply_to=obj["objection_id"],
            ),
        )
        assert rejected.is_error
        await call(
            a,
            "send",
            session_id=sessions["billing"],
            kind="resolve",
            body="Operator transport assertion complete; no implementation claim",
            request_id=run + "-resolve",
            reply_to=obj["objection_id"],
        )
        checks.append("Exact objection routes to peers; only author can resolve")
        with httpx.Client(timeout=40) as http:
            response = http.post(
                url + "/v1/tools",
                headers={
                    "Authorization": "Bearer "
                    + (credentials / "delivery.token").read_text().strip()
                },
                json={"operation": "check_in", "session_id": sessions["billing"]},
            )
            assert response.status_code == 403
        checks.append("Cross-agent session access rejected")

        # Two simultaneous updates of the same revision: exactly one may succeed.
        def race(i):
            with httpx.Client(timeout=40) as http:
                return http.post(
                    url + "/v1/tools",
                    headers={
                        "Authorization": "Bearer "
                        + (credentials / "delivery.token").read_text().strip()
                    },
                    json={
                        "operation": "send",
                        **args,
                        "body": f"Operator concurrency fixture {i}",
                        "expected_revision": 2,
                        "request_id": run + f"-race-{i}",
                    },
                ).status_code

        races = await asyncio.gather(*[asyncio.to_thread(race, i) for i in range(2)])
        assert sorted(races) == [200, 409], races
        checks.append("Concurrent policy revision has exactly one winner")
    # All local MCP processes have exited; a new process recovers the second session.
    async with connect(url, credentials / "billing.token") as recovered:
        inbox = await call(recovered, "check_in", session_id=second["session_id"])
        ids = {m["id"] for m in inbox["messages"]}
        assert sent["event_id"] in ids and updated["event_id"] in ids
        await call(recovered, "check_in", session_id=second["session_id"])
        replay = await call(recovered, "check_in", session_id=second["session_id"], after=0)
        assert sent["event_id"] in {m["id"] for m in replay["messages"]}
    checks.append(
        "Client restart recovers independent cursor; explicit replay returns earlier events"
    )
    return {
        "executed_by": "operator",
        "at": datetime.now(UTC).isoformat(),
        "url": url,
        "run_id": run,
        "topic": topic,
        "sessions": sessions,
        "policy_ids": [sent["event_id"], updated["event_id"]],
        "objection_id": obj["objection_id"],
        "passed": checks,
        "limitations": "One computer, independent MCP processes, real AWS HTTPS. "
        "No LLM comprehension, code application, or combined-code claim.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--credentials", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists; retain evidence and choose another path")
    result = asyncio.run(verify(args.url.rstrip("/"), args.credentials))
    args.output.write_text(json.dumps(result, indent=2))
    for check in result["passed"]:
        print("PASS:", check)
    print("Evidence:", args.output)


if __name__ == "__main__":
    main()
