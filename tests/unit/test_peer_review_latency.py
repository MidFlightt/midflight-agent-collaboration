from types import SimpleNamespace
from unittest.mock import patch

import pytest

from midflight.ports import ReviewerUnavailable
from midflight.theater.review_policy import PeerReviewPolicy


@pytest.mark.parametrize(
    "contradiction,decides,kind",
    [
        (True, "reviewer", "semantic_mismatch"),
        (True, "lead", "requirement_conflict"),
        (False, "reviewer", None),
    ],
)
def test_independent_second_pass_also_decides_correction(contradiction, decides, kind):
    policy = PeerReviewPolicy("test")
    finding = {"kind": "semantic_mismatch", "severity": "blocking", "explanation": "conflict"}
    with (
        patch(
            "midflight.theater.review_policy._statements",
            return_value={"requirements": [], "claims": []},
        ),
        patch.object(
            policy,
            "_call",
            return_value={
                "contradiction": contradiction,
                "why": "actual declarations",
                "decides": decides,
                "answer": "Use the approved interface.",
            },
        ) as call,
    ):
        result = policy._checked(finding, SimpleNamespace())
    assert call.call_count == 1
    assert call.call_args.args[3] == "resolve_conflict"
    if kind:
        assert result["kind"] == kind
        assert result["proposed_correction"] == "Use the approved interface."
    else:
        assert result["severity"] == "info"


@pytest.mark.parametrize(
    "response",
    [
        None,
        {},
        {"contradiction": True},
        {"contradiction": True, "decides": "reviewer", "answer": ""},
    ],
)
def test_incomplete_confirmation_cannot_become_approval(response):
    policy = PeerReviewPolicy("test")
    with (
        patch(
            "midflight.theater.review_policy._statements",
            return_value={"requirements": [], "claims": []},
        ),
        patch.object(policy, "_call", return_value=response),
        pytest.raises(ReviewerUnavailable),
    ):
        policy._checked({"severity": "blocking"}, SimpleNamespace())
