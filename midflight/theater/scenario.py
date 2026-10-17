from datetime import UTC, datetime

from midflight.domain.models import Contract, FieldType, Participant, Project, Role, Task
from midflight.ports import Commit
from midflight.services.participants import hash_token, new_token
from midflight.services.plans import PlanDraft

NAMES = ("pricing", "checkout", "reporting", "notifications")


def seed(services, project, plan_draft=None):
    names = tuple(t.id for t in plan_draft.tasks) if plan_draft else NAMES
    tokens = {name: new_token() for name in (*names, "lead")}
    people = [
        Participant(
            id=name,
            project_id=project,
            role=Role.LEAD if name == "lead" else Role.AGENT,
            developer_name=name,
            token_hash=hash_token(token),
        )
        for name, token in tokens.items()
    ]
    services.store.commit(
        Commit(
            project,
            "theater-seed",
            puts=[
                Project(
                    id=project,
                    repository="demo/commerce",
                    lead_id="lead",
                    participant_ids=list(tokens),
                ),
                *people,
            ],
        )
    )
    tasks = [
        Task(
            id=n,
            title=n.title(),
            owner=n,
            branch=n,
            provides=["price"] if n == "pricing" else ["order"] if n == "checkout" else [],
            consumes=["price"] if n == "checkout" else ["order"] if n == "reporting" else [],
        )
        for n in NAMES
    ]
    contracts = [
        Contract(
            id="price",
            version=1,
            provider_task="pricing",
            consumer_tasks=["checkout"],
            fields={"total_cents": FieldType.INTEGER},
        ),
        Contract(
            id="order",
            version=1,
            provider_task="checkout",
            consumer_tasks=["reporting"],
            fields={"total_cents": FieldType.INTEGER},
        ),
    ]
    lead = services.store.get_participant("lead")
    plan = services.plans.propose(
        lead, plan_draft or PlanDraft(requirements=[], tasks=tasks, contracts=contracts)
    )
    services.plans.approve(lead, plan.version, "initial demo plan")
    return tokens


def change(services, project):
    current = services.plans.current(project)
    contracts = [
        c.model_copy(update={"fields": {**c.fields, "currency": FieldType.STRING}})
        if c.id == "price"
        else c
        for c in current.contracts
    ]
    lead = services.store.get_participant("lead")
    proposed = services.plans.propose(
        lead, PlanDraft(requirements=current.requirements, tasks=current.tasks, contracts=contracts)
    )
    services.plans.approve(lead, proposed.version, "pricing now includes currency")
    return datetime.now(UTC).isoformat()


def subscription_direction(services, project, actor, direction):
    """One explicit product pivot for the synthetic commerce acceptance scenario."""
    from midflight.domain.models import Requirement

    if "subscription" not in direction.lower():
        raise ValueError("This demo supports the direction: We will do subscription based")
    current = services.plans.current(project)
    requirement = Requirement(
        id="subscription-billing",
        description=direction,
        acceptance_criteria=[
            'Pricing returns total_cents=1200 and billing_interval="monthly".',
            "Checkout creates a subscription order with a nonempty subscription_id "
            'and billing_interval="monthly".',
            "Reporting accepts the subscription order and returns its monthly total_cents.",
        ],
    )
    tasks = [
        t.model_copy(update={"requirement_ids": [*t.requirement_ids, requirement.id]})
        if t.id != "notifications"
        else t
        for t in current.tasks
    ]
    contracts = [
        c.model_copy(
            update={
                "fields": {
                    **c.fields,
                    "billing_interval": FieldType.STRING,
                    **({"subscription_id": FieldType.STRING} if c.id == "order" else {}),
                }
            }
        )
        for c in current.contracts
    ]
    proposed = services.plans.propose(
        actor,
        PlanDraft(
            requirements=[*current.requirements, requirement], tasks=tasks, contracts=contracts
        ),
    )
    services.plans.approve(actor, proposed.version, direction)
    return services.plans.current(project)
