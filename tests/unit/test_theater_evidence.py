import pytest

from demo_fixture import NOW
from midflight.domain.models import Directive, DirectiveSource, DirectiveState
from midflight.theater.evidence import AFFECTED, coordination_checks


def directives():
    return [
        Directive(
            id=name,
            project_id="demo",
            source=DirectiveSource.PLAN_CHANGE,
            task_id=name,
            recipient_id=name,
            plan_version=2,
            requested_adjustment="review dependency",
            reason="Graph evidence (plan v1, v2): saved dependency path.",
            created_at=NOW,
        )
        for name in sorted(AFFECTED)
    ]


def test_evidence_does_not_confuse_notification_with_acknowledgement():
    checks = coordination_checks(directives(), 2)
    assert checks["reporting_notified"] and checks["graph_evidence_saved"]
    assert not checks["affected_agents_acknowledged"]


@pytest.mark.parametrize("failure", ["missing", "old_version", "no_evidence", "superseded"])
def test_missing_or_invalid_reporting_evidence_cannot_pass(failure):
    current = directives()
    reporting = next(d for d in current if d.task_id == "reporting")
    current.remove(reporting)
    if failure != "missing":
        update = {
            "old_version": {"plan_version": 1},
            "no_evidence": {"reason": "plan changed"},
            "superseded": {"state": DirectiveState.SUPERSEDED},
        }[failure]
        current.append(reporting.model_copy(update=update))
    checks = coordination_checks(current, 2)
    assert not checks["graph_evidence_saved"]
    assert not checks["affected_agents_acknowledged"]
