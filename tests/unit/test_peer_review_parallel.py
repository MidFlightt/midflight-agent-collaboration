import threading

import pytest

from demo_fixture import make_claim, make_plan
from midflight.ports import ClaimReviewRequest, ReviewerUnavailable
from midflight.theater.review_policy import PeerReviewPolicy


def review_request():
    return ClaimReviewRequest(
        plan=make_plan(),
        claim=make_claim("T2", assumptions=["fetch() returns dict[int, dict]."]),
        other_claims=[make_claim("T1", assumptions=["fetch() returns list[dict]."])],
        rule_findings=[],
    )


FINDING = {
    "kind": "semantic_mismatch",
    "severity": "blocking",
    "explanation": "C-T2 returns a mapping from fetch(); C-T1 expects a list.",
    "affected_ids": ["C-T1", "C-T2"],
    "proposed_correction": "Original correction.",
}


def test_confirmation_and_decision_overlap_without_removing_the_confirmation_gate():
    barrier = threading.Barrier(2)

    class Reviewer(PeerReviewPolicy):
        def _call(self, system, task, data, tool, schema):
            barrier.wait(timeout=2)
            return (
                {"contradiction": True}
                if tool == "confirm_conflict"
                else {"decides": "reviewer", "answer": "Return a list."}
            )

    result = Reviewer()._checked(FINDING, review_request())
    assert result["severity"] == "blocking"
    assert result["proposed_correction"] == "Return a list."


@pytest.mark.parametrize("confirmation", [False, None, "unavailable"])
def test_a_parallel_ruling_cannot_block_without_valid_confirmation(confirmation):
    class Reviewer(PeerReviewPolicy):
        def _call(self, system, task, data, tool, schema):
            if tool == "confirm_conflict":
                if confirmation == "unavailable":
                    raise ReviewerUnavailable("offline")
                return {"contradiction": confirmation}
            return {"decides": "lead", "answer": "Must not apply this ruling."}

    result = Reviewer()._checked(FINDING, review_request())
    assert result["severity"] == "info"
    assert result["kind"] == "semantic_mismatch"
    assert result["proposed_correction"] == FINDING["proposed_correction"]


def test_unavailable_decision_preserves_the_confirmed_original_finding():
    class Reviewer(PeerReviewPolicy):
        def _call(self, system, task, data, tool, schema):
            if tool == "confirm_conflict":
                return {"contradiction": True}
            raise ReviewerUnavailable("offline")

    assert Reviewer()._checked(FINDING, review_request()) == FINDING
