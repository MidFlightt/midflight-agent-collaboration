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
                f"assert billing.summarize_records({'{}' if name == 'delivery' else '[]'})"
                "['revenue_cents']==0",
            ],
            cwd=folder,
            check=True,
        )


def test_branches_work_locally_but_their_public_interfaces_do_not_integrate(tmp_path):
    import shutil

    for owner in ["billing", "delivery"]:
        folder = tmp_path / owner
        folder.mkdir()
        write_starter(folder, owner)
        subprocess.run(
            [
                sys.executable,
                "-c",
                "import delivery,billing; "
                "delivery._records[1]={'id':1,'total_cents':1200,'refund_cents':0,"
                "'status':'confirmed'}; "
                "assert billing.summarize_records(delivery.get_delivery_records())"
                "['revenue_cents']==1200",
            ],
            cwd=folder,
            check=True,
        )
    combined = tmp_path / "combined"
    combined.mkdir()
    shutil.copy2(tmp_path / "billing/billing.py", combined / "billing.py")
    shutil.copy2(tmp_path / "delivery/delivery.py", combined / "delivery.py")
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import delivery,billing; "
            "delivery._records[1]={'id':1,'total_cents':1200,'refund_cents':0,"
            "'status':'confirmed'}; "
            "billing.summarize_records(delivery.get_delivery_records())",
        ],
        cwd=combined,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "TypeError" in result.stderr
