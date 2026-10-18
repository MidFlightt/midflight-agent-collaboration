"""The team server's settings, and the guards that keep local-only modes off the network."""

import os

import pytest
from fastapi.testclient import TestClient

from midflight.config import Settings
from midflight.repository.team import connect_commands, team_settings

VALUES = {
    "MIDFLIGHT_PUBLIC_URL": "https://midflight.example.com",
    "MIDFLIGHT_GITHUB_CLIENT_ID": "Iv1.abc",
    "MIDFLIGHT_GITHUB_CLIENT_SECRET": "secret",
    "MIDFLIGHT_GITHUB_APP_ID": "123",
}


@pytest.fixture(autouse=True)
def no_midflight_environment(monkeypatch):
    for name in list(os.environ):
        if name.startswith("MIDFLIGHT_"):
            monkeypatch.delenv(name)


def env_file(tmp_path, **overrides):
    key = tmp_path / "app.pem"
    key.write_text("-----BEGIN RSA PRIVATE KEY-----\n")
    values = VALUES | {"MIDFLIGHT_GITHUB_PRIVATE_KEY_PATH": str(key)} | overrides
    path = tmp_path / "team.env"
    path.write_text("".join(f"{k}={v}\n" for k, v in values.items()))
    path.chmod(0o600)
    return path


def settings(path, url=None):
    return team_settings(path, url, 6379, "midflight-team")


def test_first_run_writes_a_private_template_and_says_what_to_fill(tmp_path):
    path = tmp_path / "home/team.env"
    with pytest.raises(ValueError, match="Created .*Fill in"):
        settings(path)
    assert path.stat().st_mode & 0o777 == 0o600
    assert "MIDFLIGHT_GITHUB_CLIENT_SECRET=" in path.read_text()
    with pytest.raises(ValueError, match="MIDFLIGHT_PUBLIC_URL must be the HTTPS address"):
        settings(path)


def test_complete_settings_run_the_hosted_connector_on_falkordb(tmp_path):
    result = settings(env_file(tmp_path))
    assert result.backend == "falkordb" and result.falkor_graph == "midflight-team"
    assert result.public_url == "https://midflight.example.com"
    assert result.github_sign_in_configured and result.github_app_configured
    assert not result.dev_login
    assert settings(env_file(tmp_path), "https://other.example.com").public_url.endswith(
        "other.example.com"
    )


@pytest.mark.parametrize(
    "url", ["http://midflight.example.com", "https://127.0.0.1:8100", "https://localhost", ""]
)
def test_teammates_need_a_public_https_address(tmp_path, url):
    with pytest.raises(ValueError, match="HTTPS address teammates reach"):
        settings(env_file(tmp_path, MIDFLIGHT_PUBLIC_URL=url))


def test_missing_github_values_are_named_and_secrets_must_be_private(tmp_path):
    with pytest.raises(ValueError, match="MIDFLIGHT_GITHUB_CLIENT_SECRET .*client secret"):
        settings(env_file(tmp_path, MIDFLIGHT_GITHUB_CLIENT_SECRET=""))
    with pytest.raises(ValueError, match="private key .* doesn't exist"):
        settings(env_file(tmp_path, MIDFLIGHT_GITHUB_PRIVATE_KEY_PATH=str(tmp_path / "no.pem")))
    readable = env_file(tmp_path)
    readable.chmod(0o644)
    with pytest.raises(ValueError, match="chmod 600"):
        settings(readable)


def test_a_team_server_never_uses_the_dev_login(tmp_path):
    with pytest.raises(ValueError, match="never uses MIDFLIGHT_DEV_LOGIN"):
        settings(env_file(tmp_path, MIDFLIGHT_DEV_LOGIN="1"))


def test_the_dev_login_only_runs_on_this_computer():
    with pytest.raises(ValueError, match="only runs on a 127.0.0.1 or localhost URL"):
        Settings(dev_login=True, public_url="https://midflight.example.com")
    assert Settings(dev_login=True, public_url="http://localhost:9000").dev_login


def test_teammate_commands_name_only_the_public_connector():
    commands = connect_commands("https://midflight.example.com")
    assert all("https://midflight.example.com/mcp" in c for c in commands)
    assert not any("token" in c or "key" in c for c in commands)


def test_local_mode_refuses_requests_addressed_to_other_hosts():
    from types import SimpleNamespace

    from demo_fixture import NOW
    from midflight.adapters.clock import FixedClock
    from midflight.adapters.memory_store import MemoryStore
    from midflight.api.app import build_services, create_app
    from midflight.repository.cli import loopback_only
    from midflight.repository.server import add_local_routes

    services = build_services(MemoryStore(), FixedClock(NOW))
    server = SimpleNamespace(services=services, app=create_app(services))
    add_local_routes(server, "k" * 40)
    loopback_only(server.app)
    assert (
        TestClient(server.app, base_url="http://127.0.0.1:8000").get("/healthz").status_code == 200
    )
    tunnelled = TestClient(server.app, base_url="https://abc.trycloudflare.com")
    assert tunnelled.get("/healthz").status_code == 400
    assert tunnelled.post("/local/projects", json={}).status_code == 400
