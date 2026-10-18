"""Cloud launch isolation and reset safety, without making network calls."""

from types import SimpleNamespace

from fastapi.testclient import TestClient

from midflight.communication.harness import CommunicationTheater
from midflight.communication.validate import coordination_objections
from midflight.theater.interactive import terminal_app


def test_cloud_launch_uses_individual_token_file_and_local_launch_omits_url():
    live = CommunicationTheater.__new__(CommunicationTheater)
    original = {
        "MIDFLIGHT_URL": "http://127.0.0.1:8928",
        "MIDFLIGHT_TOKEN": "legacy",
        "PYTHONPATH": "/repo",
    }
    assert live.mcp_environment("billing", original.copy()) == {"PYTHONPATH": "/repo"}
    live.cloud = {"url": "https://example.com", "credentials": "/private/credentials"}
    result = live.mcp_environment("billing", original.copy())
    assert result["MIDFLIGHT_URL"] == "https://example.com"
    assert result["MIDFLIGHT_TOKEN_FILE"] == "/private/credentials/billing.token"
    assert "MIDFLIGHT_TOKEN" not in result


def test_cloud_reset_does_not_close_existing_run():
    calls = []
    live = SimpleNamespace(
        key="key", cloud={"project": "isolated"}, close=lambda: calls.append("close")
    )
    with TestClient(terminal_app(live), base_url="http://localhost") as client:
        result = client.post("/reset", headers={"x-demo-key": "key"})
        assert result.status_code == 409
        assert calls == []


def test_cloud_validation_does_not_claim_no_objections(tmp_path):
    (tmp_path / "run.json").write_text('{"cloud": {"project": "isolated"}}')
    result = coordination_objections(tmp_path)
    assert result["available"] is False
    assert result["open_objections"] is None
