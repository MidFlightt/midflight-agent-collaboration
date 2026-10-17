"""Demo check-ins expose peer assumptions only after that peer's claim is approved.

This adapter is local to the PigeonPost demo; production Midflight is unchanged.
Own verdicts and coordination directives are returned unchanged.
"""

from dataclasses import replace


def install_reviewed_assumptions(server):
    service = server.services.check_ins
    original = service.check_in
    store = server.services.store

    def check_in(*args, **kwargs):
        result = original(*args, **kwargs)
        approved = set()
        for assumption in result.assumed_by_others:
            peer = store.get_claim(assumption.claim_id)
            if peer is not None and str(peer.state) == "approved":
                approved.add(assumption.claim_id)
        return replace(
            result,
            assumed_by_others=[a for a in result.assumed_by_others if a.claim_id in approved],
            seen_assumptions=[a for a in result.seen_assumptions if a.claim_id in approved],
        )

    service.check_in = check_in

    # A technical correction should be applied by the later claimant. Keep the
    # decision itself, but do not invalidate an earlier approved reference claim.
    claims = server.services.claims
    original_settled = claims._settled

    def settled(project, plan, claim, findings, others):
        from midflight.domain.models import Claim, Directive

        protected = {
            peer.id
            for peer in others
            if str(peer.state) == "approved" and peer.created_at < claim.created_at
        }
        protected_tasks = {peer.task_id for peer in others if peer.id in protected}
        entities = original_settled(project, plan, claim, findings, others)
        return [
            entity
            for entity in entities
            if not (
                isinstance(entity, Claim)
                and entity.id in protected
                or isinstance(entity, Directive)
                and entity.task_id in protected_tasks
            )
        ]

    claims._settled = settled
    original_agreed = claims._agreed

    def agreed(project, plan, claim, others, escalations):
        # A check-in must not count as accepting a proposal that was withheld.
        return original_agreed(
            project,
            plan,
            claim,
            [peer for peer in others if str(peer.state) == "approved"],
            escalations,
        )

    claims._agreed = agreed
