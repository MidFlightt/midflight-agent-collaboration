"""The hosted connector end to end over HTTP, signing in the way an AI client does.

Starts `midflight.communication.hosted` on a free port with the dev login and in-memory
storage, then does what Claude Code, Codex, Claude or ChatGPT do when someone adds the
connector URL: discover sign-in, register, sign in, trade the code for a token, and call
the tools. Two people on "different computers" share a project through its join code.
"""

import base64
import hashlib
import json
import re
import secrets
import socket
import threading
import time
from urllib.parse import parse_qs, urlparse

import httpx
import httpx2
import pytest
import uvicorn
from mcp import Client
from mcp.client.streamable_http import streamable_http_client

from midflight.communication.hosted import create_app, memory_backend

pytestmark = pytest.mark.anyio

REDIRECT = "http://127.0.0.1:9/callback"  # the client's own page; never actually opened


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="module")
def base_url():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    url = f"http://127.0.0.1:{port}"
    registry, services = memory_backend()
    app = create_app(url, registry, services, dev_login=True)
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 15
    while not server.started:
        assert time.monotonic() < deadline, "server didn't start"
        time.sleep(0.05)
    yield url
    server.should_exit = True
    thread.join(timeout=10)


def sign_in(base_url, login):
    """Everything an AI client does to get a MidFlight token, with `login` signing in."""
    http = httpx.Client(base_url=base_url, follow_redirects=False)
    client = http.post(
        "/register",
        json={
            "client_name": "test client",
            "redirect_uris": [REDIRECT],
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "none",
        },
    )
    assert client.status_code == 201, client.text
    client_id = client.json()["client_id"]
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=")
    start = http.get(
        "/authorize",
        params={
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": REDIRECT,
            "code_challenge": challenge.decode(),
            "code_challenge_method": "S256",
            "state": "abc",
        },
    )
    assert start.status_code == 302, start.text
    page = urlparse(start.headers["location"])
    assert page.path == "/oauth/dev-login"
    pending = parse_qs(page.query)["pending"][0]
    done = http.post("/oauth/dev-login", data={"pending": pending, "login": login})
    assert done.status_code == 302, done.text
    params = parse_qs(urlparse(done.headers["location"]).query)
    assert params["state"] == ["abc"]
    tokens = http.post(
        "/token",
        data={
            "grant_type": "authorization_code",
            "code": params["code"][0],
            "redirect_uri": REDIRECT,
            "client_id": client_id,
            "code_verifier": verifier,
        },
    )
    assert tokens.status_code == 200, tokens.text
    return tokens.json() | {"client_id": client_id}


async def call(base_url, token, tool, *, error=False, **args):
    http = httpx2.AsyncClient(headers={"Authorization": f"Bearer {token}"}, timeout=30)
    async with Client(streamable_http_client(f"{base_url}/mcp", http_client=http)) as client:
        result = await client.call_tool(tool, args)
    assert result.is_error is error, result.content
    text = result.content[0].text
    return text if error else json.loads(text)


def test_unsigned_requests_point_to_sign_in_and_pages_answer(base_url):
    response = httpx.post(f"{base_url}/mcp", json={})
    assert response.status_code == 401
    assert "resource_metadata" in response.headers["www-authenticate"]
    discovery = httpx.get(f"{base_url}/.well-known/oauth-authorization-server").json()
    assert discovery["authorization_endpoint"] == f"{base_url}/authorize"
    assert discovery["registration_endpoint"] == f"{base_url}/register"
    assert httpx.get(f"{base_url}/healthz").json() == {"status": "ok"}
    landing = httpx.get(f"{base_url}/")
    assert landing.status_code == 200 and f"{base_url}/mcp" in landing.text
    # A signed-in event stream is refused instead of holding a Lambda open.
    token = sign_in(base_url, "probe")["access_token"]
    stream = httpx.get(f"{base_url}/mcp", headers={"Authorization": f"Bearer {token}"})
    assert stream.status_code == 405


async def test_two_computers_share_a_project_through_its_join_code(base_url):
    lead = sign_in(base_url, "somesh")["access_token"]
    created = await call(base_url, lead, "create_project", name="Food app")
    code = created["join_code"]

    teammate = sign_in(base_url, "frederik")["access_token"]
    joined = await call(base_url, teammate, "join_project", join_code=code)
    assert joined["lead"] == "somesh"

    orders = await call(
        base_url,
        lead,
        "join",
        name="orders",
        task="Orders",
        request_id="j",
        dependencies=["order-record"],
    )
    payments = await call(
        base_url,
        teammate,
        "join",
        name="payments",
        task="Payments",
        request_id="j",
        dependencies=["order-record"],
    )
    published = await call(
        base_url,
        lead,
        "send",
        session_id=orders["session_id"],
        kind="interface",
        topic="order-record",
        body="{id, total_cents, email}",
        request_id="p",
        expected_revision=0,
    )
    assert published["claimed_ownership"] and "payments" in published["recipients"]

    update = await call(base_url, teammate, "check_in", session_id=payments["session_id"])
    assert [i["body"] for i in update["interfaces"]] == ["{id, total_cents, email}"]

    # Tokens are personal: the teammate can't read the lead's session or take its name.
    refused = await call(
        base_url, teammate, "check_in", error=True, session_id=orders["session_id"]
    )
    assert "Unknown session" in refused
    taken = await call(
        base_url, teammate, "join", error=True, name="orders", task="x", request_id="s"
    )
    assert "belongs to somesh" in taken

    # A refreshed token is the same person in the same project.
    session = sign_in(base_url, "frederik")
    refreshed = httpx.post(
        f"{base_url}/token",
        data={
            "grant_type": "refresh_token",
            "refresh_token": session["refresh_token"],
            "client_id": session["client_id"],
        },
    ).json()["access_token"]
    [project] = (await call(base_url, refreshed, "my_projects"))["projects"]
    assert project["agents"] == {"orders": "somesh", "payments": "frederik"}
    assert project["owners"] == {"order-record": "orders"}


def test_unconfigured_deployment_is_healthy_but_explains(monkeypatch):
    from starlette.testclient import TestClient

    from midflight.communication.hosted import create_app_from_env

    monkeypatch.delenv("MIDFLIGHT_PUBLIC_URL", raising=False)
    with TestClient(create_app_from_env()) as client:
        assert client.get("/healthz").json() == {
            "status": "ok",
            "configured": False,
            "reason": "set MIDFLIGHT_PUBLIC_URL",
        }
        assert client.post("/mcp").status_code == 503


def test_memory_mode_from_environment(monkeypatch):
    from starlette.testclient import TestClient

    from midflight.communication.hosted import create_app_from_env

    monkeypatch.setenv("MIDFLIGHT_PUBLIC_URL", "http://127.0.0.1:8123/")
    monkeypatch.setenv("MIDFLIGHT_DEV_LOGIN", "1")
    monkeypatch.setenv("MIDFLIGHT_HOSTED_STORE", "memory")
    with TestClient(create_app_from_env(), base_url="http://127.0.0.1:8123") as client:
        assert client.get("/healthz").json() == {"status": "ok"}
        assert client.post("/mcp", json={}).status_code == 401


# Sign in with GitHub: a consent page and browser-bound cookies -----------------------------


class FakeGitHub:
    """Like GitHub for someone who already authorized the app: no prompt, straight back."""

    def authorize_url(self, state, redirect_uri):
        return f"https://github.example/login/oauth/authorize?state={state}"

    def account_for_code(self, code, redirect_uri):
        from midflight.ports import GitHubAccount

        return GitHubAccount(4242, "victim")


GITHUB_BASE = "https://midflight.example"


def github_client():
    from starlette.testclient import TestClient

    registry, services = memory_backend()
    app = create_app(GITHUB_BASE, registry, services, github_sign_in=FakeGitHub())
    return TestClient(app, base_url=GITHUB_BASE, follow_redirects=False)


def start_sign_in(http, redirect_uri, client_name="Claude Code"):
    client_id = http.post(
        "/register",
        json={
            "client_name": client_name,
            "redirect_uris": [redirect_uri],
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "none",
        },
    ).json()["client_id"]
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=")
    start = http.get(
        "/authorize",
        params={
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "code_challenge": challenge.decode(),
            "code_challenge_method": "S256",
            "state": "s",
        },
    )
    consent = urlparse(start.headers["location"])
    assert consent.path == "/oauth/consent"
    return client_id, verifier, parse_qs(consent.query)["pending"][0]


def test_github_sign_in_asks_for_consent_in_the_same_browser():
    with github_client() as browser:
        client_id, verifier, pending = start_sign_in(browser, REDIRECT)
        page = browser.get("/oauth/consent", params={"pending": pending})
        assert page.status_code == 200
        assert "Claude Code" in page.text and "127.0.0.1:9" in page.text
        assert page.headers["x-frame-options"] == "DENY"
        set_cookie = page.headers["set-cookie"].lower()
        assert "httponly" in set_cookie and "samesite=strict" in set_cookie
        assert "secure" in set_cookie
        csrf = re.search(r'name="csrf" value="([^"]+)"', page.text).group(1)

        to_github = browser.post("/oauth/consent", data={"pending": pending, "csrf": csrf})
        assert to_github.status_code == 302
        assert to_github.headers["location"].startswith("https://github.example/")
        assert "samesite=lax" in to_github.headers["set-cookie"].lower()

        back = browser.get("/oauth/github/callback", params={"code": "c", "state": pending})
        assert back.status_code == 302, back.text
        code = parse_qs(urlparse(back.headers["location"]).query)["code"][0]
        tokens = browser.post(
            "/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": REDIRECT,
                "client_id": client_id,
                "code_verifier": verifier,
            },
        )
        assert tokens.status_code == 200, tokens.text


def test_a_crafted_github_link_cannot_sign_someone_in_to_another_app():
    with github_client() as http:
        # The attacker registers their own client and starts a sign-in...
        _client_id, _verifier, pending = start_sign_in(http, "https://attacker.example/cb")
        # ...then sends the link to the victim, whose browser has none of their cookies.
        http.cookies.clear()
        # 1. Straight to GitHub's callback (GitHub skips its prompt): refused.
        direct = http.get("/oauth/github/callback", params={"code": "c", "state": pending})
        assert direct.status_code == 400
        assert "start in this browser" in direct.text
        # 2. A cross-site auto-submitted Continue carries no consent cookie: refused.
        forged = http.post("/oauth/consent", data={"pending": pending, "csrf": "guess"})
        assert forged.status_code == 400
        # 3. Opening the consent page shows exactly where access would go.
        page = http.get("/oauth/consent", params={"pending": pending})
        assert "attacker.example" in page.text


def test_production_without_github_credentials_explains_instead_of_crashing(monkeypatch):
    from starlette.testclient import TestClient

    from midflight.communication.hosted import create_app_from_env

    monkeypatch.setenv("MIDFLIGHT_PUBLIC_URL", "https://midflight.example")
    for name in (
        "MIDFLIGHT_DEV_LOGIN",
        "MIDFLIGHT_GITHUB_CLIENT_ID",
        "MIDFLIGHT_GITHUB_CLIENT_SECRET",
    ):
        monkeypatch.delenv(name, raising=False)
    with TestClient(create_app_from_env()) as client:
        health = client.get("/healthz").json()
        assert health["configured"] is False and "GITHUB_CLIENT_ID" in health["reason"]
        assert client.post("/mcp").status_code == 503
