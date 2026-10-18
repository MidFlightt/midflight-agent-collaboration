import hashlib
import json
import shutil
import stat

import pytest

from experiment.communication.case import DEPENDENCIES, OWNERS
from experiment.communication.local import prepare_local


def test_local_preparation_issues_separate_credentials_without_starting_services(tmp_path):
    if not shutil.which("openssl"):
        pytest.skip("OpenSSL required for local TLS preparation")
    root = tmp_path / "checkout"
    root.mkdir()
    private = tmp_path / "private"
    backend = prepare_local("ppfresh1", private, root=root)
    config = json.loads((private / "config.json").read_text())
    assert config["projects"] == {"ppfresh1": {"agents": DEPENDENCIES, "owners": OWNERS}}
    tokens = []
    for agent in DEPENDENCIES:
        path = private / (agent + ".token")
        token = path.read_text().strip()
        tokens.append(token)
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
        assert config["credentials"][hashlib.sha256(token.encode()).hexdigest()] == {
            "project": "ppfresh1",
            "agent": agent,
        }
        assert token not in (private / "config.json").read_text()
    assert len(set(tokens)) == 7
    assert stat.S_IMODE((backend / "key.pem").stat().st_mode) == 0o600
    assert (backend / "cert.pem").exists()
    assert (
        json.loads((backend / "setup.json").read_text())["status"]
        == "prepared; no services or agents started"
    )
    before = (private / "t1.token").read_bytes()
    with pytest.raises(FileExistsError):
        prepare_local("ppfresh1", private, root=root)
    assert (private / "t1.token").read_bytes() == before


def test_local_preparation_rejects_unsafe_locations_before_writing(tmp_path):
    root = tmp_path / "checkout"
    root.mkdir()
    with pytest.raises(ValueError, match="outside"):
        prepare_local("ppfresh2", root / "secret", root=root)
    with pytest.raises(ValueError, match="alphanumeric"):
        prepare_local("../other", tmp_path / "private", root=root)
    assert list(root.iterdir()) == []
    assert not (tmp_path / "private").exists()
