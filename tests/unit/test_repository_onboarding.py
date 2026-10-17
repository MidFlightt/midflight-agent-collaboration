"""A new repository uses general plans; no synthetic task seed or direction matching."""

import json
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient
from mcp import Client

from demo_fixture import NOW
from midflight.adapters.clock import FixedClock
from midflight.adapters.memory_store import MemoryStore
from midflight.api.app import build_services, create_app
from midflight.mcp.local.client import MidflightApi
from midflight.repository.cli import initialize, local_url
from midflight.repository.mcp import build_repository_server
from midflight.repository.server import add_local_routes

PID = "local-0123456789abcdef"
KEY = "setup-key-" * 5
TOKENS = {n: (n + "-token-") * 8 for n in ("lead", "backend", "emails")}
BODY = {
    "project_id": PID,
    "repository": "example/bookings",
    "identities": [{"name": n, "token": t} for n, t in TOKENS.items()],
}


def setup(store=None):
    services = build_services(store or MemoryStore(), FixedClock(NOW))
    server = SimpleNamespace(services=services, app=create_app(services))
    add_local_routes(server, KEY)
    client = TestClient(server.app)
    return services, client


def auth(name):
    return {"Authorization": "Bearer " + TOKENS[name]}


def bootstrap(client):
    response = client.post("/local/projects", json=BODY, headers={"Authorization": "Bearer " + KEY})
    assert response.status_code == 200, response.text
    return response.json()


def draft():
    return {
        "requirements": [
            {
                "id": "reservations",
                "description": "Book a seat",
                "acceptance_criteria": ["Returns a reservation identifier"],
            }
        ],
        "tasks": [
            {
                "id": "reserve",
                "title": "Reservations",
                "owner": PID + ".backend",
                "branch": "reserve",
                "provides": ["booking"],
                "requirement_ids": ["reservations"],
            },
            {
                "id": "email",
                "title": "Email confirmation",
                "owner": PID + ".emails",
                "branch": "email",
                "consumes": ["booking"],
            },
        ],
        "contracts": [
            {
                "id": "booking",
                "version": 1,
                "provider_task": "reserve",
                "consumer_tasks": ["email"],
                "fields": {"reservation_id": "string"},
            }
        ],
    }


def test_bootstrap_requires_admin_key_and_retry_preserves_state_and_hides_tokens():
    services, client = setup()
    assert client.post("/local/projects", json=BODY).status_code == 401
    assert bootstrap(client)["created"]
    assert not bootstrap(client)["created"]
    assert len(services.store.list_audit(PID)) == 1
    response = client.get(f"/local/projects/{PID}", headers=auth("backend"))
    assert response.status_code == 200
    assert response.json()["plan"] is None
    assert all(t not in response.text for t in TOKENS.values())
    assert client.get(f"/local/projects/{PID}").status_code == 401
    assert (
        client.get("/local/projects/local-ffffffffffffffff", headers=auth("backend")).status_code
        == 403
    )
    changed = {**BODY, "identities": [{"name": n, "token": (n + "different") * 8} for n in TOKENS]}
    assert (
        client.post(
            "/local/projects", json=changed, headers={"Authorization": "Bearer " + KEY}
        ).status_code
        == 409
    )


def test_member_cannot_propose_or_approve_and_non_demo_plan_is_persistent():
    services, client = setup()
    bootstrap(client)
    path = f"/projects/{PID}/plans"
    assert client.post(path, json=draft(), headers=auth("backend")).status_code == 403
    response = client.post(path, json=draft(), headers=auth("lead"))
    assert response.status_code == 201, response.text
    assert (
        client.post(
            path + "/1/approve", json={"reason": "Human approved"}, headers=auth("backend")
        ).status_code
        == 403
    )
    assert (
        client.post(
            path + "/1/approve", json={"reason": "Human approved"}, headers=auth("lead")
        ).status_code
        == 200
    )
    assert services.plans.current(PID).tasks[0].id == "reserve"
    assert services.store.get_participant(PID + ".backend").role.value == "agent"


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_general_mcp_lead_workflow_and_agent_tool_boundary():
    _, http = setup()
    bootstrap(http)
    lead_api = MidflightApi(TestClient(http.app, headers=auth("lead")), PID)
    async with Client(build_repository_server(lead_api, "lead")) as client:
        context = await client.call_tool("project_context", {})
        assert not context.is_error
        result = await client.call_tool("propose_plan", draft())
        assert not result.is_error, result.content
        version = json.loads(result.content[0].text)["version"]
        result = await client.call_tool(
            "approve_plan", {"version": version, "reason": "Human reviewed bookings plan"}
        )
        assert not result.is_error, result.content
    api = MidflightApi(TestClient(http.app, headers=auth("backend")), PID)
    async with Client(build_repository_server(api, "agent")) as client:
        names = {t.name for t in (await client.list_tools()).tools}
        assert "propose_plan" not in names and "approve_plan" not in names
        result = await client.call_tool("check_in", {"task_id": "reserve"})
        assert not result.is_error
        assert "reservation_id" in result.content[0].text


def test_init_preserves_repository_files_and_retries_with_saved_credentials(tmp_path, monkeypatch):
    import subprocess

    from midflight.repository import cli

    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    (repo / "AGENTS.md").write_text("Existing team rules.\n")
    (repo / ".gitignore").write_text("build/\n")
    home = tmp_path / "home"
    home.mkdir()
    (home / "setup.key").write_text(KEY)
    services, testclient = setup()

    def handle(request):
        response = testclient.request(
            request.method, request.url.path, content=request.content, headers=request.headers
        )
        return httpx.Response(response.status_code, json=response.json())

    real_client = httpx.Client
    monkeypatch.setattr(
        cli.httpx, "Client", lambda **kw: real_client(transport=httpx.MockTransport(handle))
    )
    first = initialize(repo, "http://127.0.0.1:8000", "example/new", ["worker"], home)
    second = initialize(repo, "http://127.0.0.1:8000", "example/new", ["worker"], home)
    assert first == second
    guide = (repo / "MIDFLIGHT.md").read_text()
    assert "Terminal → New Terminal" in guide
    assert "--identity lead" in guide and "--identity worker" in guide
    assert first["identities"]["worker"]["token"] not in guide
    assert (repo / "AGENTS.md").read_text().startswith("Existing team rules.")
    assert (repo / "AGENTS.md").read_text().count("<!-- midflight:start -->") == 1
    assert (repo / ".midflight/private.json").stat().st_mode & 0o777 == 0o600
    assert (repo / ".gitignore").read_text().startswith("build/")
    config = (repo / ".midflight/mcp-worker.json").read_text()
    assert first["identities"]["worker"]["token"] not in config
    assert services.store.get_project(first["project_id"])


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com",
        "http://evil.example",
        "http://localhost/path",
        "http://user@localhost",
    ],
)
def test_local_setup_never_sends_credentials_to_remote_urls(url):
    with pytest.raises(ValueError):
        local_url(url)


def test_codex_launcher_has_no_scripted_scenario_or_permission_overrides(tmp_path):
    from midflight.repository.cli import codex_command

    command = codex_command(tmp_path, "backend")
    assert command[:3] == ["codex", "-C", str(tmp_path)]
    assert "mcp_servers.midflight_repository" in command[-1]
    assert "private.json" not in command[-1]
    assert "--dangerously-bypass-approvals-and-sandbox" not in command
    assert "subscription" not in " ".join(command)
    assert (
        codex_command(tmp_path, "backend", "Implement assigned task")[-1]
        == "Implement assigned task"
    )


def test_explicit_session_tool_approval_excludes_plan_writes(tmp_path):
    from midflight.repository.cli import codex_command

    command = codex_command(tmp_path, "backend", approve_tools=True)
    assert any('tools.check_in.approval_mode="approve"' in arg for arg in command)
    assert not any("tools.approve_plan" in arg or "tools.propose_plan" in arg for arg in command)


def test_standard_server_does_not_expose_local_bootstrap_and_bad_identities_reject():
    services = build_services(MemoryStore(), FixedClock(NOW))
    with pytest.raises(ValueError, match="setup key"):
        add_local_routes(SimpleNamespace(services=services, app=create_app(services)), "")
    ordinary = TestClient(create_app(services))
    assert ordinary.post("/local/projects", json=BODY).status_code == 404
    _, client = setup()
    duplicate = {**BODY, "identities": [BODY["identities"][0], BODY["identities"][0]]}
    assert (
        client.post(
            "/local/projects", json=duplicate, headers={"Authorization": "Bearer " + KEY}
        ).status_code
        == 422
    )
    assert services.store.get_project(PID) is None


def test_existing_credentials_cannot_restore_a_revoked_participant():
    services, client = setup()
    bootstrap(client)
    services.participants.revoke(
        services.store.get_participant(PID + ".lead"), PID + ".emails", "Removed by human"
    )
    response = client.post("/local/projects", json=BODY, headers={"Authorization": "Bearer " + KEY})
    assert response.status_code == 409
    assert client.get(f"/local/projects/{PID}", headers=auth("emails")).status_code == 401


def test_start_guide_preserves_owner_edits(tmp_path):
    from midflight.repository.workspace import install_start_guide

    (tmp_path / "MIDFLIGHT.md").write_text("Team-specific startup notes")
    install_start_guide(tmp_path, {})
    assert (tmp_path / "MIDFLIGHT.md").read_text() == "Team-specific startup notes"
