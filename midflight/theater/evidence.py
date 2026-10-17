"""Acceptance checks for the demo's persisted graph directives."""

from midflight.domain.models import Directive, DirectiveSource, DirectiveState

AFFECTED = {"pricing", "checkout", "reporting"}


def coordination_checks(directives: list[Directive], version: int) -> dict[str, bool]:
    current = [
        d
        for d in directives
        if d.plan_version == version
        and d.source is DirectiveSource.PLAN_CHANGE
        and d.state is not DirectiveState.SUPERSEDED
    ]
    recipients = {d.task_id for d in current}
    expected = [d for d in current if d.task_id in AFFECTED]
    return {
        "pricing_and_checkout_notified": {"pricing", "checkout"} <= recipients,
        "reporting_notified": "reporting" in recipients,
        "notifications_unaffected": "notifications" not in recipients,
        "graph_evidence_saved": recipients >= AFFECTED
        and all("Graph evidence (plan " in d.reason for d in expected),
        "affected_agents_acknowledged": recipients >= AFFECTED
        and all(d.state is DirectiveState.ACKNOWLEDGED for d in expected),
    }
