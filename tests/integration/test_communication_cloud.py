"""Authenticated, independent clients against isolated real FalkorDB state."""

import hashlib
import uuid
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest
from fastapi.testclient import TestClient

from midflight.communication.cloud import RemoteService, build_app
from midflight.communication.store import Store


@pytest.fixture
def cloud(falkor_server):
    prefix = "cloudtest_" + uuid.uuid4().hex
    agents = {"billing": ["records", "fee"], "delivery": ["records", "fee"], "booking": []}
    config = {
        "projects": {
            p: {"agents": agents, "owners": {"records": "delivery"}} for p in ("one", "two")
        },
        "credentials": {
            hashlib.sha256(token.encode()).hexdigest(): {"project": p, "agent": a}
            for token, p, a in [
                ("a", "one", "billing"),
                ("b", "one", "delivery"),
                ("c", "one", "booking"),
                ("d", "two", "billing"),
            ]
        },
    }

    def factory(project):
        return Store(prefix + project, falkor_server.port)

    def app():
        return build_app(config, factory)

    yield app
    for p in config["projects"]:
        store = factory(p)
        store.graph.delete()
        store.close()


def rpc(client, token, operation, **args):
    return client.post(
        "/v1/tools",
        headers={"Authorization": "Bearer " + token},
        json={"operation": operation, **args},
    )


def join(client, token, name, key="join"):
    response = rpc(client, token, "join", name=name, task="Implement component", request_id=key)
    assert response.status_code == 200, response.text
    return response.json()["session_id"]


def test_credentials_bind_project_agent_and_sessions(cloud):
    with TestClient(cloud()) as client:
        a = join(client, "a", "billing")
        assert client.get("/healthz").status_code == 200
        assert rpc(client, "bad", "check_in", session_id=a).status_code == 401
        assert rpc(client, "b", "check_in", session_id=a).status_code == 403
        assert rpc(client, "d", "check_in", session_id=a).status_code == 403
        assert (
            rpc(
                client, "a", "join", name="delivery", task="x", request_id="impersonate"
            ).status_code
            == 403
        )
        assert (
            rpc(
                client, "b", "join", name="delivery", task="x", request_id="resume", session_id=a
            ).status_code
            == 403
        )
        assert rpc(client, "a", "check_in", session_id=a, project="two").status_code == 422
        assert rpc(client, "a", "check_in", session_id=a, after=True).status_code == 422
        assert rpc(client, "a", "agree", session_id=a).status_code == 422
        other = join(client, "d", "billing")
        assert other != a


def test_policy_delivery_supersession_and_recovery(cloud):
    with TestClient(cloud()) as client:
        a = join(client, "a", "billing")
        a2 = join(client, "a", "billing", "independent")
        b = join(client, "b", "delivery")
        c = join(client, "c", "booking")
        args = dict(
            session_id=b,
            kind="policy",
            body="Keep four credits",
            source="Keep four",
            topic="fee",
            request_id="fee",
            expected_revision=0,
        )
        first = rpc(client, "b", "send", **args).json()
        assert first["recipients"] == ["billing", "delivery"]
        assert rpc(client, "b", "send", **args).json()["duplicate"]
        assert rpc(client, "b", "send", **(args | {"body": "different"})).status_code == 409
        second = rpc(
            client,
            "b",
            "send",
            **(args | {"request_id": "fee2", "body": "Keep five", "expected_revision": 1}),
        ).json()
        updates = rpc(client, "a", "check_in", session_id=a).json()
        assert [p["id"] for p in updates["unapplied_policies"]] == [second["event_id"]]
        assert updates["policy_history"][0]["superseded_by"] == second["event_id"]
        assert all(not p["applied_report_ids"] for p in updates["policy_history"])
        assert rpc(client, "c", "check_in", session_id=c).json()["messages"] == []
    # Rebuild the application, connections, and provisioning; retain database state.
    with TestClient(cloud()) as recovered:
        assert rpc(recovered, "a", "check_in", session_id=a).json()["messages"] == []
        replay = rpc(recovered, "a", "check_in", session_id=a2).json()
        assert [m["id"] for m in replay["messages"]] == [first["event_id"], second["event_id"]]
        assert rpc(recovered, "b", "send", **args).json()["event_id"] == first["event_id"]


def test_concurrent_publications_and_author_only_resolution(cloud):
    with TestClient(cloud()) as client:
        a = join(client, "a", "billing")
        b = join(client, "b", "delivery")
        base = dict(session_id=b, kind="interface", topic="records", expected_revision=0)
        with ThreadPoolExecutor(2) as pool:
            responses = list(
                pool.map(
                    lambda i: rpc(
                        client, "b", "send", **base, body=f"Mapping version {i}", request_id=f"p{i}"
                    ),
                    range(2),
                )
            )
        assert sorted(r.status_code for r in responses) == [200, 409]
        publication = next(r.json() for r in responses if r.status_code == 200)
        args = dict(
            session_id=a,
            publication_id=publication["event_id"],
            revision=1,
            problem="Missing saved refunds",
            affects="Historical revenue",
            request_id="obj",
        )
        objection = rpc(client, "a", "object", **args).json()
        assert objection["recipients"] == ["billing", "delivery"]
        assert (
            rpc(client, "a", "object", **args).json()["objection_id"] == objection["objection_id"]
        )
        assert (
            rpc(client, "a", "object", **(args | {"revision": 9, "request_id": "bad"})).status_code
            == 409
        )
        resolution = dict(
            kind="resolve",
            body="Saved refunds now included",
            request_id="resolve",
            reply_to=objection["objection_id"],
        )
        assert rpc(client, "b", "send", session_id=b, **resolution).status_code == 409
        assert rpc(client, "a", "send", session_id=a, **resolution).status_code == 200


def test_bridge_serialization_and_error_sanitization(cloud):
    with TestClient(cloud(), base_url="https://shared.example") as client:
        remote = RemoteService("https://shared.example", "a", client)
        joined = remote.join("billing", "Implement billing", "j", None, None)
        assert remote.check_in(joined["session_id"])["agent"] == "billing"
        with pytest.raises(ValueError, match="403"):
            remote.join("delivery", "Impersonate", "wrong")
    with pytest.raises(ValueError, match="HTTPS"):
        RemoteService("http://shared.example", "secret")

    def timeout(request):
        raise httpx.ReadTimeout("secret URL must not leak")

    remote = RemoteService(
        "https://shared.example", "secret", httpx.Client(transport=httpx.MockTransport(timeout))
    )
    with pytest.raises(ValueError, match="identical request_id/input"):
        remote.join("billing", "x", "j")
    remote.close()


def test_restart_preserves_ownership_transfer_and_body_limit(cloud):
    with TestClient(cloud()) as client:
        a = join(client, "a", "billing")
        b = join(client, "b", "delivery")
        response = rpc(
            client,
            "b",
            "send",
            session_id=b,
            kind="transfer",
            topic="records",
            new_owner="billing",
            expected_revision=1,
            body="Billing maintains records",
            request_id="transfer",
        )
        assert response.status_code == 200, response.text
        assert client.post("/v1/tools", content=b"x" * 65537).status_code == 413
    with TestClient(cloud()) as client:
        context = rpc(client, "a", "check_in", session_id=a).json()
        assert context["interface_owners"]["records"] == {"name": "billing", "revision": 2}
