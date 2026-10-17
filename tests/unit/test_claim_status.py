from datetime import timedelta
from types import SimpleNamespace

from demo_fixture import NOW, make_claim
from midflight.domain.models import ClaimState
from midflight.theater.claim_status import claim_statuses


def store(latest, revisions=None):
    return SimpleNamespace(
        list_claims=lambda project: latest,
        get_claim=lambda claim_id, revision: (revisions or {}).get((claim_id, revision)),
    )


def test_status_comes_from_verdict_not_agent_prose():
    claim = make_claim(
        state=ClaimState.APPROVED, assumptions=["NEEDS_REVISION FAILED ERROR"], revision=1
    )
    status = claim_statuses(store([claim]), "demo", ["T2", "idle"])
    assert status["T2"]["state"] == "approved"
    assert status["T2"]["claim_id"] == claim.id
    assert status["idle"]["state"] == "ready"


def test_revised_approval_retains_actual_prior_rejection():
    rejected = make_claim(id="C-1", state=ClaimState.NEEDS_REVISION, revision=1)
    approved = rejected.model_copy(update={"revision": 2, "state": ClaimState.APPROVED})
    status = claim_statuses(store([approved], {("C-1", 1): rejected}), "demo", ["T2"])["T2"]
    assert status["state"] == "approved"
    assert [(h["revision"], h["state"]) for h in status["history"]] == [
        (1, "needs_revision"),
        (2, "approved"),
    ]


def test_new_claim_beats_high_revision_of_old_claim():
    older = make_claim(id="C-1", revision=9, state=ClaimState.APPROVED, created_at=NOW)
    newer = older.model_copy(
        update={
            "id": "C-2",
            "revision": 1,
            "state": ClaimState.PENDING,
            "created_at": NOW + timedelta(seconds=1),
        }
    )
    status = claim_statuses(store([older, newer]), "demo", ["T2"])["T2"]
    assert status["claim_id"] == "C-2" and status["state"] == "pending"
