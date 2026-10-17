"""Client-neutral peer MCP: no special lead and no preset product pivot."""

import os
from contextlib import suppress

import httpx

from midflight.mcp.local.adapter import build_server
from midflight.services.plans import PlanDraft
from midflight.theater.agent_mcp import ObservedApi
from midflight.theater.peer_setup import CHECKPOINT_POLICY, PEER_CHECK_IN, PEER_SUBMIT_CLAIM

PEER_INSTRUCTIONS = (
    "All sessions are equal peers. Any human can give a direction in their session.\n"
    + CHECKPOINT_POLICY
    + "\nFor a substantive human product change use read_shared_plan, then publish_shared_plan "
    "with the version read, the human's direction and complete updated plan. "
    "If the product choice is ambiguous ask the human."
)


def main():
    api = ObservedApi.connect(
        os.environ["MIDFLIGHT_URL"], os.environ["MIDFLIGHT_TOKEN"], os.environ["MIDFLIGHT_PROJECT"]
    )
    server = build_server(
        api,
        instructions=PEER_INSTRUCTIONS,
        tool_descriptions={"check_in": PEER_CHECK_IN, "submit_claim": PEER_SUBMIT_CLAIM},
    )
    client = httpx.Client(
        base_url=os.environ["MIDFLIGHT_DEMO_CONTROLLER"],
        headers={"Authorization": "Bearer " + os.environ["MIDFLIGHT_TOKEN"]},
        timeout=30,
    )

    def arrive():
        # Startup telemetry must not prevent the agent from using coordination tools.
        with suppress(httpx.HTTPError):
            client.post("/peer-arrival", timeout=3).raise_for_status()

    arrive()

    @server.tool(
        description="Read the whole shared plan before proposing a product direction change."
    )
    def read_shared_plan() -> dict:
        arrive()
        response = client.get("/peer-plan")
        response.raise_for_status()
        return response.json()

    @server.tool(
        description=(
            "Publish a shared-plan update requested directly by the human in this "
            "session. Supply their direction, the current version and the complete "
            "updated plan. Preserve unrelated requirements and existing task "
            "identities. A stale version is refused: reread and rebase."
        )
    )
    def publish_shared_plan(expected_version: int, direction: str, plan: PlanDraft) -> dict:
        response = client.post(
            "/peer-plan",
            json={
                "expected_version": expected_version,
                "direction": direction,
                "plan": plan.model_dump(mode="json"),
            },
        )
        return {"accepted": response.is_success, "result": response.json()}

    server.run("stdio")


if __name__ == "__main__":
    main()
