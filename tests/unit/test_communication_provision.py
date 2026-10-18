import hashlib
import json
import stat

import pytest

from midflight.communication.provision import provision


def test_provision_issues_individual_private_tokens_without_overwriting(tmp_path):
    output = tmp_path / "private"
    provision(
        "team", {"billing": ["records"], "delivery": ["records"]}, {"records": "delivery"}, output
    )
    config = json.loads((output / "config.json").read_text())
    tokens = []
    for agent in ("billing", "delivery"):
        path = output / (agent + ".token")
        token = path.read_text().strip()
        tokens.append(token)
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
        assert config["credentials"][hashlib.sha256(token.encode()).hexdigest()] == {
            "project": "team",
            "agent": agent,
        }
        assert token not in (output / "config.json").read_text()
    assert tokens[0] != tokens[1]
    original = (output / "billing.token").read_text()
    with pytest.raises(FileExistsError):
        provision("team", {"billing": []}, {}, output)
    assert (output / "billing.token").read_text() == original


def test_invalid_identity_does_not_write_outside_output(tmp_path):
    with pytest.raises(ValueError, match="agent identifier"):
        provision("team", {"../escape": []}, {}, tmp_path / "private")
    assert list(tmp_path.iterdir()) == []
