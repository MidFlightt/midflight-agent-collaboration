"""Experimental equal-permission plan publishing for an isolated four-peer project."""

import threading

from fastapi import HTTPException

from midflight.services.errors import ServiceError
from midflight.services.plans import PlanDraft
from midflight.theater.scenario import NAMES


def content(plan):
    data = {
        key: plan.model_dump(mode="json")[key] for key in ("requirements", "tasks", "contracts")
    }
    for contract in data["contracts"]:
        contract.pop("version", None)
    return data


class PeerCoordination:
    def __init__(self, services, project, *, names=NAMES, preserve_tasks=True):
        self.services, self.project = services, project
        self.lock = threading.RLock()
        self.names, self.preserve_tasks = names, preserve_tasks

    def actor(self, name):
        actor = self.services.store.get_participant(name)
        if (
            name not in self.names
            or actor is None
            or not actor.active
            or actor.project_id != self.project
        ):
            raise HTTPException(403, "Not an active peer in this project")
        return actor

    def read(self, name):
        self.actor(name)
        return self.services.plans.current(self.project)

    def publish(self, name: str, expected_version: int, direction: str, draft: PlanDraft):
        actor = self.actor(name)
        if not direction.strip() or len(direction) > 4000:
            raise HTTPException(422, "Supply the human's product direction (1–4000 characters)")
        with self.lock:
            current = self.read(name)
            if expected_version != current.version:
                if (
                    expected_version == current.version - 1
                    and current.change_reason == direction
                    and content(current) == content(draft)
                ):
                    return current, True
                raise HTTPException(
                    409, f"Plan is now v{current.version}. Read it and rebase your change."
                )
            before = {(t.id, t.owner, t.branch) for t in current.tasks}
            after = {(t.id, t.owner, t.branch) for t in draft.tasks}
            if self.preserve_tasks and before != after:
                raise HTTPException(
                    422, "Preserve the four existing task identities, owners and branches"
                )
            if not self.preserve_tasks and any(t.owner not in self.names for t in draft.tasks):
                raise HTTPException(422, "Tasks must belong to an active lab participant")
            if content(current) == content(draft):
                raise HTTPException(422, "No plan changes were supplied")
            try:
                proposed = self.services.plans.propose(actor, draft)
                return self.services.plans.approve(actor, proposed.version, direction), False
            except ServiceError as error:
                raise HTTPException(error.status, error.detail) from error
