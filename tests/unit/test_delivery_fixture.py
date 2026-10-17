import subprocess
import sys

from demo_fixture import NOW
from midflight.adapters.clock import FixedClock
from midflight.adapters.memory_store import MemoryStore
from midflight.api.app import build_services
from midflight.domain.models import Role
from midflight.ports import Commit
from midflight.services.plans import PlanDraft
from midflight.theater.delivery_fixture import CANCELLATION_DIRECTION, initial_plan, write_starter
from midflight.theater.peer_coordination import PeerCoordination
from midflight.theater.scenario import seed


def test_policy_change_only_notifies_billing_and_delivery():
    services = build_services(MemoryStore(), FixedClock(NOW))
    seed(services, "deliveries", initial_plan())
    actor = services.store.get_participant("billing").model_copy(update={"role": Role.LEAD})
    services.store.commit(Commit("deliveries", "peer", puts=[actor]))
    peers = PeerCoordination(services, "deliveries")
    plan = peers.read("billing")
    draft = PlanDraft.model_validate(
        plan.model_dump(include={"requirements", "tasks", "contracts"})
    )
    draft.requirements[:] = [
        r.model_copy(
            update={
                "description": CANCELLATION_DIRECTION,
                "acceptance_criteria": [
                    "Refund max(total_cents - 400, 0).",
                    "Billing reports total_cents minus saved refund_cents.",
                ],
            }
        )
        if r.id == "cancellation-policy"
        else r
        for r in draft.requirements
    ]
    updated, _ = peers.publish("billing", 1, CANCELLATION_DIRECTION, draft)
    assert {d.task_id for d in services.store.list_directives("deliveries")} == {
        "billing",
        "delivery",
    }
    assert [c.fields for c in plan.contracts] == [c.fields for c in updated.contracts]


def test_delivery_starters_import_and_reproduce_the_interface_drift(tmp_path):
    for name in ["billing", "delivery", "booking", "notifications"]:
        folder = tmp_path / name
        folder.mkdir()
        write_starter(folder, name)
        shape = "dict" if name == "delivery" else "list"
        subprocess.run(
            [
                sys.executable,
                "-c",
                "import app,delivery,billing; "
                f"assert type(delivery.get_delivery_records()).__name__=='{shape}'; "
                "assert billing.summarize_records([])['revenue_cents']==0",
            ],
            cwd=folder,
            check=True,
        )
