import copy
import json
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from midflight.communication.cloud import build_app
from midflight.communication.invites import Invites, digest
from midflight.communication.onboard import install


class MemoryStore:
    def __init__(self):
        self.revision = 0
        self.state = dict(agents={}, sessions={}, events=[], requests={}, dependencies={})
        self.lock = threading.Lock()

    def read(self):
        with self.lock:
            return self.revision, copy.deepcopy(self.state)

    def commit(self, revision, state):
        with self.lock:
            if revision != self.revision:
                return False
            self.state = copy.deepcopy(state)
            self.revision += 1
            return True

    def recipients(self, revision, topics):
        return sorted(
            n for n, a in self.state["agents"].items() if set(topics) & set(a["dependencies"])
        )

    def close(self):
        pass


def test_isolated_redemptions_stable_retries_and_no_plaintext_tokens():
    store = MemoryStore()
    registry = Invites(store, "k" * 32)
    invite = registry.create(2, 1, 2)
    a = registry.redeem(invite["id"], invite["secret"], "a" * 32)
    b = registry.redeem(invite["id"], invite["secret"], "b" * 32)
    assert a["project"] != b["project"]
    assert len(a["tokens"]) == 4
    assert registry.redeem(invite["id"], invite["secret"], "a" * 32) == a
    restarted = Invites(store, "k" * 32)
    assert restarted.redeem(invite["id"], invite["secret"], "a" * 32) == a
    for token in a["tokens"].values():
        assert token not in json.dumps(store.state)
        assert restarted.authenticate(token)[0]["project"] == a["project"]
    assert invite["secret"] not in json.dumps(store.state)
    with pytest.raises(ValueError, match="remaining"):
        registry.redeem(invite["id"], invite["secret"], "c" * 32)


def test_concurrent_last_place_and_duplicate_redemptions():
    registry = Invites(MemoryStore(), "k" * 32)
    invite = registry.create(1, 1, 1)

    def redeem(key):
        try:
            return registry.redeem(invite["id"], invite["secret"], key * 32)
        except ValueError:
            return None

    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(redeem, ["a", "b"]))
    assert sum(x is not None for x in results) == 1
    invite = registry.create(1, 1, 1)
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(redeem, ["a", "a"]))
    assert results[0] == results[1]


def test_expiry_revocation_and_wrong_secret():
    now = [0]
    registry = Invites(MemoryStore(), "k" * 32, lambda: now[0])
    invite = registry.create(3, 1, 2)
    with pytest.raises(PermissionError):
        registry.info(invite["id"], "wrong")
    access = registry.redeem(invite["id"], invite["secret"], "a" * 32)
    token = access["tokens"]["billing"]
    now[0] = 3600
    with pytest.raises(PermissionError):
        registry.redeem(invite["id"], invite["secret"], "a" * 32)
    assert registry.authenticate(token)
    now[0] = 7200
    assert registry.authenticate(token) is None
    now[0] = 0
    registry.revoke(invite["id"])
    assert registry.authenticate(token) is None
    with pytest.raises(PermissionError):
        registry.info(invite["id"], invite["secret"])


def test_http_auth_and_project_isolation_survive_app_restart():
    stores = {}
    config = {
        "projects": {"existing": {"agents": {"billing": []}}},
        "credentials": {digest("existing"): {"project": "existing", "agent": "billing"}},
    }

    def app():
        return build_app(
            config,
            lambda p: stores.setdefault(p, MemoryStore()),
            invite_key="k" * 32,
            invite_admin_hash=digest("operator"),
        )

    with TestClient(app()) as client:
        assert client.post("/v1/invites", json={}).status_code == 401
        invite = client.post(
            "/v1/invites", json={}, headers={"Authorization": "Bearer operator"}
        ).json()
        request = dict(id=invite["id"], secret=invite["secret"], request_id="a" * 32)
        access = client.post("/v1/invites/redeem", json=request)
        assert access.headers["cache-control"] == "no-store"
        a = access.json()
        b = client.post("/v1/invites/redeem", json=request | {"request_id": "b" * 32}).json()

        def join(token, name):
            return client.post(
                "/v1/tools",
                headers={"Authorization": "Bearer " + token},
                json=dict(operation="join", name=name, task="Build", request_id="j"),
            )

        sid = join(a["tokens"]["billing"], "billing").json()["session_id"]
        assert join(a["tokens"]["billing"], "delivery").status_code == 403
        assert (
            client.post(
                "/v1/tools",
                headers={"Authorization": "Bearer " + b["tokens"]["billing"]},
                json=dict(operation="check_in", session_id=sid),
            ).status_code
            == 403
        )
        assert join("existing", "billing").status_code == 200
    with TestClient(app()) as client:
        assert client.post("/v1/invites/redeem", json=request).json() == a
        headers = {"Authorization": "Bearer " + a["tokens"]["billing"]}
        assert (
            client.post(
                "/v1/tools", headers=headers, json=dict(operation="check_in", session_id=sid)
            ).status_code
            == 200
        )
        assert (
            client.delete(
                "/v1/invites/" + invite["id"], headers={"Authorization": "Bearer operator"}
            ).status_code
            == 200
        )
        assert (
            client.post(
                "/v1/tools", headers=headers, json=dict(operation="check_in", session_id=sid)
            ).status_code
            == 401
        )


def test_installer_private_files_and_no_overwrite(tmp_path):
    r = Invites(MemoryStore(), "k" * 32)
    i = r.create(1, 1, 1)
    b = r.redeem(i["id"], i["secret"], "a" * 32) | {"url": "https://example.com"}
    folder = install(b, tmp_path / "access")
    assert folder.stat().st_mode & 0o777 == 0o700
    for p in folder.iterdir():
        assert p.stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError):
        install(b, folder)
    with pytest.raises(ValueError):
        install(b | {"url": "http://example.com"}, tmp_path / "unsafe")
    with pytest.raises(ValueError):
        install(b | {"project": "../../escape"}, tmp_path / "unsafe")
    assert not (tmp_path / "unsafe").exists()


def test_signing_key_cannot_silently_change_recovered_credentials():
    store = MemoryStore()
    Invites(store, "k" * 32)
    with pytest.raises(ValueError, match="signing key changed"):
        Invites(store, "z" * 32)
