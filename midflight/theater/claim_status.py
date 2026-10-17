"""Compact, authoritative claim verdicts for coding-pane headers."""


def claim_statuses(store, project, names):
    claims = store.list_claims(project)
    result = {}
    for name in names:
        own = [c for c in claims if c.task_id == name]
        if not own:
            result[name] = {"state": "ready", "claim_id": None, "history": []}
            continue
        # A new claim ID takes precedence over a high revision of an older claim.
        claim = max(own, key=lambda c: (c.created_at, c.revision, c.id))
        history = []
        for revision in range(max(1, claim.revision - 5), claim.revision + 1):
            previous = claim if revision == claim.revision else store.get_claim(claim.id, revision)
            if previous is None:
                continue
            history.append(
                {
                    "revision": previous.revision,
                    "state": previous.state.value,
                    "findings": [f.model_dump(mode="json") for f in previous.findings],
                }
            )
        result[name] = {
            "state": claim.state.value,
            "claim_id": claim.id,
            "revision": claim.revision,
            "plan_version": claim.plan_version,
            "findings": [f.model_dump(mode="json") for f in claim.findings],
            "history": history,
        }
    return result
