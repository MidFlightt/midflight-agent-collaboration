from demo_fixture import NOW
from midflight.adapters.clock import FixedClock
from midflight.adapters.memory_store import MemoryStore
from midflight.api.app import build_services
from midflight.domain.models import ClaimState
from midflight.services.claims import ClaimSubmission
from midflight.theater.app import Theater
from midflight.theater.scenario import change, seed


def test_four_agent_scenario_selects_direct_dependents():
    services = build_services(MemoryStore(), FixedClock(NOW))
    seed(services, "demo")
    plan = services.plans.current("demo")
    for task in plan.tasks:

        def uses(ids):
            return [{"contract_id": i, "fields": plan.contract(i).fields} for i in ids]

        services.claims.submit(
            services.store.get_participant(task.owner),
            ClaimSubmission(
                task_id=task.id,
                branch=task.branch,
                base_sha="abcdef1",
                plan_version=1,
                files=[task.id + ".py"],
                acceptance_criteria=["implements contract"],
                provides=uses(task.provides),
                consumes=uses(task.consumes),
                no_interfaces=not (task.provides or task.consumes),
            ),
        )
    assert all(c.state is ClaimState.APPROVED for c in services.store.list_claims("demo"))
    change(services, "demo")
    assert {d.task_id for d in services.store.list_directives("demo")} == {"pricing", "checkout"}


def test_integration_is_independent_and_fails_missing_or_wrong_code(tmp_path):
    theater = Theater.__new__(Theater)
    theater.root = tmp_path
    theater.changed = False
    assert not theater.integration()["passed"]
    code = {
        "pricing": 'def price(): return {"total_cents":1200}',
        "checkout": "def checkout(price): return dict(price)",
        "reporting": 'def report(order): return order["total_cents"]',
        "notifications": 'def notify(email): return "Subscribed: " + email',
    }
    for name, text in code.items():
        (tmp_path / name).mkdir()
        (tmp_path / name / (name + ".py")).write_text(text)
    assert theater.integration()["passed"]
    theater.changed = True
    assert not theater.integration()["passed"]
    (tmp_path / "pricing" / "pricing.py").write_text(
        'def price(): return {"total_cents":1200,"currency":"USD"}'
    )
    assert theater.integration()["passed"]


def test_subscription_integration_requires_interval_and_subscription_identity(tmp_path):
    theater = Theater.__new__(Theater)
    theater.root, theater.changed, theater.subscription = tmp_path, True, True
    code = {
        "pricing": 'def price(): return {"total_cents":1200,"billing_interval":"monthly"}',
        "checkout": "def checkout(price): return dict(price)",
        "reporting": 'def report(order): return order["total_cents"]',
        "notifications": 'def notify(email): return "Subscribed: " + email',
    }
    for name, source in code.items():
        (tmp_path / name).mkdir()
        (tmp_path / name / (name + ".py")).write_text(source)
    assert not theater.integration()["passed"]
    (tmp_path / "checkout" / "checkout.py").write_text(
        'def checkout(price): return {**price,"subscription_id":"sub-demo"}'
    )
    assert theater.integration()["passed"]
