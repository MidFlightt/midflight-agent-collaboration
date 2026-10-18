"""Authenticated RPC for the four tools; never exposes the database or runs models."""

import hashlib
import hmac
import inspect
import json
import os
import re
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Literal

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from .service import Service
from .store import Store


class Arguments(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Join(Arguments):
    operation: Literal["join"]
    name: str = Field(max_length=60)
    task: str = Field(max_length=300)
    request_id: str = Field(max_length=120)
    session_id: str | None = None
    dependencies: list[str] | None = None


class Send(Arguments):
    operation: Literal["send"]
    session_id: str
    kind: str
    body: str = Field(max_length=2000)
    request_id: str = Field(max_length=120)
    to: list[str] | None = None
    topic: str = ""
    reply_to: int | None = None
    expected_revision: int | None = None
    source: str = Field(default="", max_length=2000)
    depends_on: list[str] | None = None
    new_owner: str | None = None


class CheckIn(Arguments):
    operation: Literal["check_in"]
    session_id: str
    after: int | None = None


class Object(Arguments):
    operation: Literal["object"]
    session_id: str
    publication_id: int
    revision: int
    problem: str = Field(max_length=2000)
    affects: str = Field(max_length=2000)
    request_id: str = Field(max_length=120)
    alternative: str = Field(default="", max_length=2000)


Operation = Annotated[Join | Send | CheckIn | Object, Field(discriminator="operation")]


def validate_config(config):
    """Only operator-defined projects/identities exist. Store token hashes, not tokens."""
    if not config.get("projects") or not config.get("credentials"):
        raise ValueError("Configure projects and credentials before starting")
    for project, settings in config["projects"].items():
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", project):
            raise ValueError("Invalid project identifier")
        if not settings.get("agents"):
            raise ValueError("Configure at least one agent")
        for agent, topics in settings["agents"].items():
            if not re.fullmatch(r"[A-Za-z0-9_-]{1,60}", agent):
                raise ValueError("Invalid agent identifier")
            if not isinstance(topics, list) or any(
                not isinstance(t, str) or not t.strip() or len(t) > 120 for t in topics
            ):
                raise ValueError("Agent dependencies must be topic names")
        if any(
            not isinstance(t, str) or not t.strip() or len(t) > 120
            for t in settings.get("owners", {})
        ):
            raise ValueError("Owned topics must be nonempty topic names")
        if any(a not in settings["agents"] for a in settings.get("owners", {}).values()):
            raise ValueError("Owners must be configured agents")
    for digest, identity in config["credentials"].items():
        if not re.fullmatch(r"[a-f0-9]{64}", digest):
            raise ValueError("Credentials must be SHA256 token hashes")
        settings = config["projects"].get(identity["project"], {})
        if identity["agent"] not in settings.get("agents", {}):
            raise ValueError("Credential must identify a configured project and agent")


def build_app(config, store_factory=None, *, invite_key=None, invite_admin_hash=None):
    validate_config(config)
    if store_factory is None:

        def store_factory(project):
            return Store(
                "shared_" + project,
                int(os.environ.get("MIDFLIGHT_DB_PORT", "6379")),
                host=os.environ.get("MIDFLIGHT_DB_HOST", "127.0.0.1"),
            )

    if bool(invite_key) != bool(invite_admin_hash):
        raise ValueError("Configure both invite signing key and operator hash")
    if invite_admin_hash and not re.fullmatch(r"[a-f0-9]{64}", invite_admin_hash):
        raise ValueError("Invite operator credential must be a SHA256 hash")
    services = {}
    service_lock = threading.RLock()
    registry = None
    if invite_key and invite_admin_hash:
        from .invites import Invites

        registry = Invites(store_factory("invite_registry"), invite_key)

    def get_service(project, settings):
        with service_lock:
            if project in services:
                return services[project]
            service = Service(store_factory(project))

            def provision(state, revision):
                for agent, topics in settings["agents"].items():
                    state["agents"].setdefault(agent, {"task": "", "dependencies": topics})
                for topic, owner in settings.get("owners", {}).items():
                    state.setdefault("owners", {}).setdefault(topic, {"name": owner, "revision": 1})
                return {}

            try:
                service._mutate(provision)
            except Exception:
                service.store.close()
                raise
            services[project] = service
            return service

    @asynccontextmanager
    async def lifespan(app):
        try:
            for project, settings in config["projects"].items():
                get_service(project, settings)
            yield
        finally:
            for service in services.values():
                service.store.close()
            if registry:
                registry.service.store.close()

    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)

    if registry:
        from .invite_api import routes

        routes(app, registry, invite_admin_hash)

    @app.middleware("http")
    async def bounded_body(request: Request, call_next):
        chunks, size = [], 0
        async for chunk in request.stream():
            size += len(chunk)
            if size > 65536:
                return JSONResponse({"detail": "Request exceeds 64 KiB"}, status_code=413)
            chunks.append(chunk)
        request._body = b"".join(chunks)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.get("/healthz")
    def health():
        try:
            for project in config["projects"]:
                services[project].store.read()
            if registry:
                registry.service.store.read()
        except Exception:
            raise HTTPException(503, "Coordination storage unavailable") from None
        return {"status": "ok"}

    @app.post("/v1/tools")
    def invoke(payload: Operation, authorization: str = Header(default="")):
        token = authorization.removeprefix("Bearer ") if authorization.startswith("Bearer ") else ""
        digest = hashlib.sha256(token.encode()).hexdigest()
        identity = (
            next(
                (v for k, v in config["credentials"].items() if hmac.compare_digest(k, digest)),
                None,
            )
            if token
            else None
        )
        if identity is None and registry and token:
            try:
                match = registry.authenticate(token)
                if match:
                    identity, settings = match
                    get_service(identity["project"], settings)
            except Exception:
                raise HTTPException(503, "Credential storage unavailable") from None
        if identity is None:
            raise HTTPException(401, "Invalid credentials", headers={"WWW-Authenticate": "Bearer"})
        service = services[identity["project"]]
        args = payload.model_dump(exclude={"operation"})
        if payload.operation == "join" and args["name"] != identity["agent"]:
            raise HTTPException(403, "Credential belongs to a different agent")
        sid = args.get("session_id")
        try:
            # Session->agent mapping is immutable; identity is checked before any cursor/write.
            if sid is not None or payload.operation != "join":
                session = service.store.read()[1]["sessions"].get(sid)
                if not session or session["agent"] != identity["agent"]:
                    raise HTTPException(403, "Session not accessible to this credential")
            return getattr(service, payload.operation)(**args)
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from None
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(
                503, "Backend unavailable; retry writes with identical request_id"
            ) from None

    return app


def create_app():
    if os.environ.get("MIDFLIGHT_CONFIG_JSON"):
        config = json.loads(os.environ["MIDFLIGHT_CONFIG_JSON"])
    else:
        config = json.loads(Path(os.environ["MIDFLIGHT_CONFIG"]).read_text())
    return build_app(
        config,
        invite_key=os.environ.get("MIDFLIGHT_INVITE_KEY"),
        invite_admin_hash=os.environ.get("MIDFLIGHT_INVITE_ADMIN_HASH"),
    )


class RemoteService:
    """Local stdio MCP bridge. One credential chooses project+agent server-side."""

    def __init__(self, url, token, client=None):
        import httpx

        if not url.startswith("https://"):
            raise ValueError("MIDFLIGHT_URL must use HTTPS")
        self.client = client or httpx.Client(timeout=30, follow_redirects=False)
        self.url = url.rstrip("/") + "/v1/tools"
        self.token = token

    def __getattr__(self, operation):
        if operation not in {"join", "send", "check_in", "object"}:
            raise AttributeError(operation)

        def call(*args, **kwargs):
            import httpx

            bound = inspect.signature(getattr(Service, operation)).bind(None, *args, **kwargs)
            payload = {k: v for k, v in bound.arguments.items() if k != "self"}
            try:
                response = self.client.post(
                    self.url,
                    json={"operation": operation, **payload},
                    headers={"Authorization": "Bearer " + self.token},
                )
            except httpx.HTTPError:
                raise ValueError(
                    "Connection failed; retry writes with identical request_id/input"
                ) from None
            if response.status_code != 200:
                if response.status_code == 409:
                    raise ValueError(response.json()["detail"])
                raise ValueError(
                    f"Shared backend returned HTTP {response.status_code}; "
                    "check credentials or retry unchanged after recovery"
                )
            return response.json()

        call.__name__ = operation
        return call

    def close(self):
        self.client.close()
