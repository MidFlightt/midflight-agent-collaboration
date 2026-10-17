"""Explicitly enabled local administration; normal deployments have no bootstrap route."""

from __future__ import annotations

import secrets
import threading

from fastapi import APIRouter, HTTPException, Request
from pydantic import Field

from midflight.adapters.clock import SystemClock
from midflight.domain.models import Model, Participant, Project, Role
from midflight.ports import Commit
from midflight.services.audit import audit_event
from midflight.services.participants import hash_token


class Identity(Model):
    name: str = Field(pattern=r"^[a-z][a-z0-9-]{0,31}$")
    token: str = Field(min_length=32, max_length=200, repr=False)


class Bootstrap(Model):
    project_id: str = Field(pattern=r"^local-[a-f0-9]{16}$")
    repository: str = Field(pattern=r"^[\w.-]+/[\w.-]+$")
    identities: list[Identity] = Field(min_length=1, max_length=16)


def add_local_routes(server, setup_key: str):
    router = APIRouter()
    services = server.services

    bootstrap_lock = threading.Lock()

    def initialize_project(request: Request, body: Bootstrap):
        if not secrets.compare_digest(
            request.headers.get("authorization", ""), "Bearer " + setup_key
        ):
            raise HTTPException(401, "Local setup key required")
        names = [i.name for i in body.identities]
        if (
            len(set(names)) != len(names)
            or names.count("lead") != 1
            or len({i.token for i in body.identities}) != len(names)
        ):
            raise HTTPException(422, "Unique names and tokens, including one lead, are required")
        people = [
            Participant(
                id=f"{body.project_id}.{i.name}",
                project_id=body.project_id,
                role=Role.LEAD if i.name == "lead" else Role.AGENT,
                developer_name=i.name,
                agent_name=i.name,
                token_hash=hash_token(i.token),
            )
            for i in body.identities
        ]
        project = Project(
            id=body.project_id,
            repository=body.repository,
            name=body.repository,
            lead_id=f"{body.project_id}.lead",
            participant_ids=[p.id for p in people],
        )
        existing = services.store.get_project(project.id)
        if existing:
            valid = (
                existing.repository == project.repository and existing.lead_id == project.lead_id
            )
            valid = valid and set(existing.participant_ids) == set(project.participant_ids)
            for p in people:
                saved = services.store.get_participant(p.id)
                valid = valid and saved is not None and saved.active and saved.role == p.role
                valid = valid and saved.token_hash == p.token_hash if saved else False
            if not valid:
                raise HTTPException(409, "Project exists with different or revoked identities")
            return {"project_id": project.id, "created": False}
        if services.store.find_project_by_repository(project.repository):
            raise HTTPException(
                409, "Repository already registered; use its existing private config"
            )
        key = f"local-bootstrap:{project.id}"
        event = audit_event(
            services.store,
            SystemClock(),
            project_id=project.id,
            actor=project.lead_id,
            action="project.local_created",
            entity_ids=[project.id, *project.participant_ids],
            reason="Explicit local repository initialization",
            correlation_id=key,
            idempotency_key=key,
        )
        services.store.commit(
            Commit(project.id, key, puts=[project, *people], audit=[event], expected_coord_rev=0)
        )
        return {"project_id": project.id, "created": True}

    @router.post("/local/projects")
    def bootstrap(request: Request, body: Bootstrap):
        # Serialize local administration in the supported single-server deployment.
        # Store commits still enforce atomicity/idempotency and graph consistency.
        with bootstrap_lock:
            return initialize_project(request, body)

    @router.get("/local/projects/{pid}")
    def context(pid: str, request: Request):
        token = request.headers.get("authorization", "").removeprefix("Bearer ")
        actor = services.participants.authenticate(token)
        if actor is None:
            raise HTTPException(401, "Invalid or revoked participant token")
        if actor.project_id != pid:
            raise HTTPException(403, "Different project")
        project = services.store.get_project(pid)
        plan = (
            services.store.get_plan(pid, project.current_plan_version)
            if project.current_plan_version
            else None
        )
        members = [services.store.get_participant(i) for i in project.participant_ids]
        return {
            "project_id": pid,
            "repository": project.repository,
            "you": {"id": actor.id, "role": actor.role.value},
            "members": [
                {"id": p.id, "name": p.agent_name, "role": p.role.value}
                for p in members
                if p and p.active
            ],
            "plan": plan.model_dump(mode="json") if plan else None,
        }

    # Main mounts the hosted connector at '/'; REST routes must precede that catch-all.
    server.app.router.routes[0:0] = router.routes
