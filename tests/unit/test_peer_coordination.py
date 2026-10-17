from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi import HTTPException

from demo_fixture import NOW
from midflight.adapters.clock import FixedClock
from midflight.adapters.memory_store import MemoryStore
from midflight.api.app import build_services
from midflight.domain.models import FieldType, Role
from midflight.ports import Commit
from midflight.services.plans import PlanDraft
from midflight.theater.peer_coordination import PeerCoordination
from midflight.theater.peers import PeerTheater
from midflight.theater.scenario import NAMES, seed


@pytest.fixture
def peers():
    services = build_services(MemoryStore(), FixedClock(NOW))
    seed(services, "peers")
    services.store.commit(
        Commit(
            "peers",
            "permissions",
            puts=[
                services.store.get_participant(n).model_copy(update={"role": Role.LEAD})
                for n in NAMES
            ],
        )
    )
    return PeerCoordination(services, "peers")


def changed(peers, field):
    draft = PlanDraft.model_validate(
        peers.read("pricing").model_dump(include={"tasks", "requirements", "contracts"})
    )
    draft.contracts[0].fields[field] = FieldType.STRING
    return draft


@pytest.mark.parametrize("name", NAMES)
def test_any_peer_can_publish_a_non_subscription_change(peers, name):
    plan, replayed = peers.publish(name, 1, "Prices need a currency", changed(peers, "currency"))
    assert plan.version == 2 and plan.approved_by == name and not replayed
    assert {d.task_id for d in peers.services.store.list_directives("peers")} == {
        "pricing",
        "checkout",
    }


def test_retries_do_not_create_extra_versions(peers):
    draft = changed(peers, "currency")
    peers.publish("reporting", 1, "Currency", draft)
    plan, replayed = peers.publish("reporting", 1, "Currency", draft)
    assert replayed and plan.version == 2
    assert peers.read("checkout").version == 2


def test_concurrent_peer_edits_refuse_stale_overwrite(peers):
    a, b = changed(peers, "currency"), changed(peers, "region")

    def publish(name, draft):
        try:
            return peers.publish(name, 1, name, draft)[0].version
        except HTTPException as error:
            return error.status_code

    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda pair: publish(*pair), [("checkout", a), ("reporting", b)]))
    assert sorted(results) == [2, 409]
    plan = peers.read("notifications")
    assert ("currency" in plan.contracts[0].fields) != ("region" in plan.contracts[0].fields)


def test_unregistered_identity_and_task_reassignment_are_refused(peers):
    with pytest.raises(HTTPException) as error:
        peers.publish("lead", 1, "Currency", changed(peers, "currency"))
    assert error.value.status_code == 403
    draft = changed(peers, "currency")
    draft.tasks[0] = draft.tasks[0].model_copy(update={"owner": "notifications"})
    with pytest.raises(HTTPException) as error:
        peers.publish("reporting", 1, "Currency", draft)
    assert error.value.status_code == 422
    assert peers.read("pricing").version == 1


def test_every_peer_has_direct_short_prompt_and_same_tools():
    peer = PeerTheater.__new__(PeerTheater)
    prompts = {peer.initial_prompt(n, "old script") for n in NAMES}
    assert len(prompts) == 4
    assert all("TASK.md" not in prompt and len(prompt.split()) < 25 for prompt in prompts)
    assert all(peer.plan_tools(n) == ["read_shared_plan", "publish_shared_plan"] for n in NAMES)


def test_startup_prefills_editable_drafts_without_enter():
    import threading

    peer = PeerTheater.__new__(PeerTheater)
    peer.stop_event = threading.Event()
    peer.panes = {name: name for name in NAMES}
    calls = []

    def tmux(*args):
        calls.append(args)
        return "Ask Codex to do anything" if args[0] == "capture-pane" else ""

    peer.tmux = tmux
    peer.prepare_prompts()
    assert not peer.submit_initial_prompt
    sends = [call for call in calls if call[0] == "send-keys"]
    assert len(sends) == 4
    assert {call[-1] for call in sends} == {peer.initial_prompt(n, "") for n in NAMES}
    assert all(call[3] == "-l" for call in sends)
    assert not any("Enter" in call for call in calls)


def test_plan_changes_do_not_start_idle_agent_turns(peers):
    from types import SimpleNamespace

    peer = PeerTheater.__new__(PeerTheater)
    peer.theater = SimpleNamespace(project="peers", server=SimpleNamespace(services=peers.services))

    def unexpected_terminal_input(*args):
        pytest.fail(f"Idle agent received terminal input: {args}")

    peer.tmux = unexpected_terminal_input
    peers.publish("pricing", 1, "Prices need currency", changed(peers, "currency"))
    peer._checkpoints()
    assert {d.task_id for d in peers.services.store.list_directives("peers")} == {
        "pricing",
        "checkout",
    }
    assert all(d.state.value == "queued" for d in peers.services.store.list_directives("peers"))
