import subprocess
import sys

from demo_fixture import NOW
from midflight.adapters.clock import FixedClock
from midflight.adapters.memory_store import MemoryStore
from midflight.api.app import build_services
from midflight.domain.models import FieldType, Role
from midflight.ports import Commit
from midflight.services.plans import PlanDraft
from midflight.theater.peer_coordination import PeerCoordination
from midflight.theater.scenario import seed
from midflight.theater.shop_fixture import (
    EXPIRY_DIRECTION,
    PROMPTS,
    initial_plan,
    write_starter,
)


def test_expiry_change_routes_only_to_price_provider_and_consumer():
    services = build_services(MemoryStore(), FixedClock(NOW))
    seed(services, "shop", initial_plan())
    store = services.store
    store.commit(
        Commit(
            "shop",
            "peers",
            puts=[store.get_participant(n).model_copy(update={"role": Role.LEAD}) for n in PROMPTS],
        )
    )
    peers = PeerCoordination(services, "shop")
    current = peers.read("pricing")
    assert current.version == 1
    assert all(task.requirement_ids for task in current.tasks)
    draft = PlanDraft.model_validate(
        current.model_dump(include={"requirements", "tasks", "contracts"})
    )
    draft.contracts[0].fields["expires_at"] = FieldType.INTEGER
    updated, _ = peers.publish("pricing", 1, EXPIRY_DIRECTION, draft)
    assert updated.version == 2
    assert {d.task_id for d in store.list_directives("shop")} == {"pricing", "checkout"}
    assert store.list_directives("shop", "reporting") == []
    assert store.list_directives("shop", "notifications") == []
    assert updated.contracts[1].fields == {"total_cents": FieldType.INTEGER}


def test_starter_runs_and_has_a_real_checkout_route(tmp_path):
    write_starter(tmp_path)
    subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    # The checkout routing already exists; the agent's job is to implement its module.
    subprocess.run(
        [
            sys.executable,
            "-c",
            """
import app
assert app.dispatch('/quote', {'unit_cents': 1200}) == {'total_cents': 1200}
try:
    app.dispatch('/checkout', {'price': {'total_cents': 1200}})
except NotImplementedError:
    pass
else:
    raise AssertionError('Checkout must start unfinished')
""",
        ],
        cwd=tmp_path,
        check=True,
    )
