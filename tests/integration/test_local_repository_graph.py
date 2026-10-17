"""Fresh project, graph impact, and store reconnection through the local onboarding API."""

from unit.test_repository_onboarding import PID, TOKENS, auth, bootstrap, draft, setup


def test_new_repository_plan_survives_reconnect_and_selects_dependents(falkor_store):
    from midflight.adapters.falkor_store import FalkorStore

    _, client = setup(falkor_store)
    bootstrap(client)
    path = f"/projects/{PID}/plans"
    response = client.post(path, json=draft(), headers=auth("lead"))
    assert response.status_code == 201, response.text
    assert (
        client.post(
            path + "/1/approve", json={"reason": "Human accepted bookings"}, headers=auth("lead")
        ).status_code
        == 200
    )
    # A fresh adapter/service must recognize the same credentials and approved plan.
    reconnected = FalkorStore(falkor_store.graph)
    _, restarted = setup(reconnected)
    context = restarted.get(f"/local/projects/{PID}", headers=auth("backend"))
    assert context.status_code == 200
    assert context.json()["plan"]["version"] == 1
    assert all(token not in context.text for token in TOKENS.values())
    changed = draft()
    changed["contracts"][0]["fields"]["seat_number"] = "integer"
    assert restarted.post(path, json=changed, headers=auth("lead")).status_code == 201
    response = restarted.post(
        path + "/2/approve",
        json={"reason": "Human requested seat assignment"},
        headers=auth("lead"),
    )
    assert response.status_code == 200, response.text
    ds = reconnected.list_directives(PID)
    assert {d.task_id for d in ds} == {"reserve", "email"}
    checked = restarted.post(
        f"/projects/{PID}/check-in", json={"task_id": "email"}, headers=auth("emails")
    )
    assert checked.status_code == 200, checked.text
    assert "seat_number" in checked.text
