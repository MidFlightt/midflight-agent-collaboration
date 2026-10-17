import unittest
from dataclasses import dataclass
from datetime import UTC
from types import SimpleNamespace

from midflight.theater.reviewed_assumptions import install_reviewed_assumptions


@dataclass(frozen=True)
class Reply:
    assumed_by_others: list
    seen_assumptions: list
    claim: object
    directives: list


class ReviewedAssumptionsTest(unittest.TestCase):
    def test_later_conflict_preserves_earlier_approval_and_keeps_the_decision(self):
        from datetime import datetime, timedelta

        from midflight.domain.models import Claim, ClaimState, Directive

        now = datetime.now(UTC)
        earlier = Claim.model_construct(
            id="first",
            task_id="COMMERCE",
            state=ClaimState.APPROVED,
            created_at=now - timedelta(seconds=10),
        )
        incoming = Claim.model_construct(id="second", task_id="OPERATIONS", created_at=now)
        invalidated = earlier.model_copy(update={"state": ClaimState.NEEDS_REVISION})
        directive = Directive.model_construct(task_id="COMMERCE")
        decision = object()
        claim_service = SimpleNamespace(
            _settled=lambda *a: [decision, invalidated, directive], _agreed=lambda *a: []
        )
        server = SimpleNamespace(
            services=SimpleNamespace(
                claims=claim_service,
                check_ins=SimpleNamespace(check_in=lambda: None),
                store=SimpleNamespace(),
            )
        )
        install_reviewed_assumptions(server)
        self.assertEqual(claim_service._settled(None, None, incoming, [], [earlier]), [decision])

    def test_unapproved_peer_cannot_redirect_approved_work(self):
        assumption = SimpleNamespace(claim_id="peer")
        own_verdict = object()
        directives = [object()]
        reply = Reply([assumption], [assumption], own_verdict, directives)
        peer = SimpleNamespace(state="pending")
        service = SimpleNamespace(check_in=lambda *a, **k: reply)
        server = SimpleNamespace(
            services=SimpleNamespace(
                check_ins=service,
                store=SimpleNamespace(get_claim=lambda _: peer),
                claims=SimpleNamespace(_settled=lambda *a: [], _agreed=lambda *a: []),
            )
        )
        install_reviewed_assumptions(server)
        for state in ["draft", "pending", "needs_revision", "human_review_required"]:
            peer.state = state
            actual = service.check_in("actor", "task")
            self.assertEqual(actual.assumed_by_others, [])
            self.assertEqual(actual.seen_assumptions, [])
            self.assertIs(actual.claim, own_verdict)
            self.assertIs(actual.directives, directives)
        peer.state = "approved"
        actual = service.check_in("actor", "task")
        self.assertEqual(actual.assumed_by_others, [assumption])
        self.assertEqual(actual.seen_assumptions, [assumption])

    def test_hidden_proposal_cannot_be_recorded_as_accepted(self):
        seen = []

        def record(project, plan, claim, others, escalations):
            seen.extend(others)
            return []

        claims = SimpleNamespace(_settled=lambda *a: [], _agreed=record)
        server = SimpleNamespace(
            services=SimpleNamespace(
                claims=claims,
                check_ins=SimpleNamespace(check_in=lambda: None),
                store=SimpleNamespace(),
            )
        )
        install_reviewed_assumptions(server)
        approved = SimpleNamespace(state="approved")
        claims._agreed(
            None,
            None,
            None,
            [SimpleNamespace(state="pending"), approved, SimpleNamespace(state="needs_revision")],
            [],
        )
        self.assertEqual(seen, [approved])


if __name__ == "__main__":
    unittest.main()
