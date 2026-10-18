"""The hosted MidFlight connector: add one URL, sign in, create or join a project, coordinate.

    https://<host>/mcp

Everyone adds the same connector to their coding client (Claude Code, Codex, Claude,
ChatGPT) and signs in with GitHub. Nobody clones a repository or handles a token file.

1. A lead asks their agent to `create_project` and shares the join code it returns.
2. Teammates, on any computer, ask their agents to `join_project` with that code.
3. Each agent calls `join` with its component's agent name, then coordinates with the
   same `send`, `check_in` and `objection` tools as the local prototype.

The coordination engine is `Service` unchanged, with one hosted rule: the first agent to
publish an interface on an unowned topic owns it (no operator roster). The lead can
reassign owners. An agent name belongs to the member who first joined with it.

Run locally (no GitHub secrets, in-memory storage, a sign-in form instead of GitHub):

    MIDFLIGHT_DEV_LOGIN=1 MIDFLIGHT_HOSTED_STORE=memory \\
        uv run uvicorn midflight.communication.hosted:create_app_from_env --factory --port 8000
    claude mcp add --transport http midflight http://127.0.0.1:8000/mcp
"""

import html
import os
import threading
from urllib.parse import urlparse

from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions, RevocationOptions
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, Response

from .activity import activity
from .hosted_registry import FalkorAuth, MemoryAuth, Registry
from .mcp import INSTRUCTIONS
from .service import Service

HOSTED_INTRO = """MidFlight hosted connector. Work happens inside a project shared by a team.
If the person has no project yet, call create_project with a short name and tell them the
join code to share with teammates. A teammate calls join_project with that code. my_projects
lists projects, members, agent names, owners and join codes. Then call join with project_id
(optional when the person is in exactly one project), a stable agent name for this component
and its task. send, check_in and objection take the session_id that join returns.
"""

REPLACEMENTS = {
    "No assigned owner: share an\nintention and ask the human to assign ownership.": (
        "No owner yet: the first agent to\npublish kind=interface on a topic "
        "(expected_revision=0) becomes its owner. Check\ninterface_owners first; if another "
        "agent owns the topic, message or object instead.\nThe project lead can reassign owners."
    ),
    "This is a trusted local prototype; agent names are labels, not authenticated identities.": (
        "You are signed in. In a project each agent name belongs to the teammate who first "
        "joined with it;\nuse a distinct, stable name per component and keep it across chats."
    ),
}


def hosted_instructions():
    text = INSTRUCTIONS
    for old, new in REPLACEMENTS.items():
        if old not in text:
            raise RuntimeError(f"Hosted instructions drifted from the prototype: {old!r}")
        text = text.replace(old, new)
    return HOSTED_INTRO + text


def _signed_in_user_id():
    token = get_access_token()
    return token.subject if token else None


def build_hosted_server(
    registry,
    service_for,
    *,
    auth=None,
    oauth=None,
    current_user_id=_signed_in_user_id,
):
    """The connector's MCP server. Tests pass `current_user_id` instead of real sign-in."""
    server = MCPServer(
        "midflight",
        instructions=hosted_instructions(),
        auth=auth,
        auth_server_provider=oauth,
    )

    def me():
        uid = current_user_id()
        if uid is None:
            raise ToolError("You aren't signed in to MidFlight; reconnect the connector")
        return uid

    def run(action):
        try:
            return action()
        except (ValueError, RuntimeError) as error:
            raise ToolError(str(error)) from error

    def coordinate(operation, call, args):
        result = run(call)
        # Keep all structured evidence; put the readable factual footer last.
        return result | {"activity": activity(operation, result, args)}

    def with_owners(view):
        owners = service_for(view["project_id"]).store.read()[1].get("owners", {})
        return view | {"owners": {topic: o["name"] for topic, o in sorted(owners.items())}}

    # Projects -----------------------------------------------------------------------------

    @server.tool()
    def create_project(name: str) -> dict:
        """Create a project for your team. You become its lead; share the join code."""
        uid = me()
        view = run(lambda: registry.create_project(uid, name))
        return view | {
            "next": (
                f"Share join code {view['join_code']} with teammates: they add the MidFlight "
                "connector and ask their agent to join_project with it. Then call join."
            )
        }

    @server.tool()
    def join_project(join_code: str) -> dict:
        """Join a teammate's project with the join code they shared (MF-XXXX-XXXX)."""
        uid = me()
        view = run(lambda: registry.join_project(uid, join_code))
        return with_owners(view) | {
            "next": "Call join with this project_id, your component's agent name and task."
        }

    @server.tool()
    def my_projects() -> dict:
        """Your projects: role, join code, members, agent names and topic owners."""
        uid = me()
        return {"projects": [with_owners(v) for v in run(lambda: registry.projects_of(uid))]}

    # The four coordination tools ----------------------------------------------------------

    @server.tool()
    def join(
        name: str,
        task: str,
        request_id: str,
        project_id: str | None = None,
        session_id: str | None = None,
        dependencies: list[str] | None = None,
    ) -> dict:
        """Join/recover context as one agent. Optional dependencies replaces subscriptions.

        project_id may be omitted when you belong to exactly one project. The agent name
        is reserved for you in that project the first time you use it.
        """
        uid = me()

        def act():
            project = registry.project_for(uid, project_id)
            pid = project["project_id"]
            if session_id is not None and registry.session(uid, session_id) != (pid, name):
                raise ValueError("That session belongs to another agent or project")
            registry.bind_agent(uid, pid, name)
            result = service_for(pid).join(name, task, request_id, session_id, dependencies)
            registry.record_session(uid, pid, name, result["session_id"])
            return result | {"project_id": pid, "project": project["name"]}

        return coordinate("join", act, (name, task, request_id, session_id, dependencies))

    def session_service(session_id):
        pid, _agent = registry.session(me(), session_id)
        return service_for(pid)

    @server.tool()
    def send(
        session_id: str,
        kind: str,
        body: str,
        request_id: str,
        to: list[str] | None = None,
        topic: str = "",
        reply_to: int | None = None,
        expected_revision: int | None = None,
        source: str = "",
        depends_on: list[str] | None = None,
        new_owner: str | None = None,
    ) -> dict:
        """Communicate with named peers or graph subscribers; no broadcast default.

        Kinds: intention, message, question, answer, policy, applied,
        implementation, verification, dependency, interface, resolve, transfer.
        interface: owner publishes a default using topic and expected_revision; no acceptance
        step. The first interface on an unowned topic makes you its owner.
        resolve: objection author references objection ID in reply_to with how it was addressed
        in body. transfer: current owner supplies topic,new_owner,expected_revision of ownership.
        Publication revision starts at 1; updates require expected_revision. Policy requires
        verbatim human source and topic. Answer/applied require reply_to. A dependency declares
        topic prerequisites in depends_on. Reports are agent evidence, not verification.
        """
        args = (
            session_id,
            kind,
            body,
            request_id,
            to,
            topic,
            reply_to,
            expected_revision,
            source,
            depends_on,
            new_owner,
        )
        return coordinate("send", lambda: session_service(session_id).send(*args), args)

    @server.tool()
    def check_in(session_id: str, after: int | None = None) -> dict:
        """New relevant messages and outstanding work. No polling while idle.

        after replays from a cursor already received. Drain more=true before relying
        on current context. Each session has its own persistent cursor.
        """
        args = (session_id, after)
        return coordinate("check_in", lambda: session_service(session_id).check_in(*args), args)

    @server.tool()
    def objection(
        session_id: str,
        publication_id: int,
        revision: int,
        problem: str,
        affects: str,
        request_id: str,
        alternative: str = "",
    ) -> dict:
        """Record a problem with an exact interface/policy revision. Solution optional.

        affects identifies the violated requirement or dependency. Returns stable objection_id.
        Only its author resolves through send(kind='resolve', reply_to=objection_id, body=how).
        Publication, tests, silence and supersession never resolve an objection.
        """
        args = (session_id, publication_id, revision, problem, affects, request_id, alternative)
        return coordinate("object", lambda: session_service(session_id).object(*args), args)

    # Lead tools ---------------------------------------------------------------------------

    @server.tool()
    def assign_owner(project_id: str, topic: str, agent: str) -> dict:
        """Lead only. Make a joined agent the owner of a topic; its subscribers are told."""
        uid = me()

        def act():
            lead = registry.lead_login(uid, project_id)
            return service_for(project_id).assign_owner(topic, agent, f"lead:{lead}")

        return run(act)

    @server.tool()
    def rotate_join_code(project_id: str) -> dict:
        """Lead only. Replace the join code; the old one stops working."""
        uid = me()
        return run(lambda: registry.rotate_join_code(uid, project_id))

    @server.tool()
    def remove_member(project_id: str, login: str) -> dict:
        """Lead only. Remove a member by GitHub login; their agent names are released."""
        uid = me()
        return run(lambda: registry.remove_member(uid, project_id, login))

    return server


# The web app ------------------------------------------------------------------------------


def _allowed_hosts(public_url):
    """Only answer requests addressed to our own host (protects against DNS rebinding)."""
    url = urlparse(public_url)
    if url.hostname in ("127.0.0.1", "localhost"):
        hosts = ["127.0.0.1:*", "localhost:*", "127.0.0.1", "localhost"]
        origins = ["http://127.0.0.1:*", "http://localhost:*"]
    else:
        hosts = [url.netloc]
        origins = [f"{url.scheme}://{url.netloc}"]
    return TransportSecuritySettings(allowed_hosts=hosts, allowed_origins=origins)


def _without_event_stream(mcp_app):
    """Answer a signed-in `GET /mcp` with 405, as the MCP specification allows.

    MidFlight answers each request by itself and sends no server events. Holding a GET
    stream open would keep a whole Lambda busy until it times out. Without a token the
    request passes through, so the client still gets the "sign in first" answer.
    """

    async def app(scope, receive, send):
        wants_stream = (
            scope["type"] == "http"
            and scope["method"] == "GET"
            and scope["path"].rstrip("/") == "/mcp"
            and any(name == b"authorization" for name, _value in scope["headers"])
        )
        if wants_stream:
            await Response(status_code=405, headers={"Allow": "POST"})(scope, receive, send)
        else:
            await mcp_app(scope, receive, send)

    return app


def _landing(public_url):
    url = html.escape(f"{public_url}/mcp")
    return f"""<!doctype html><meta charset="utf-8"><title>MidFlight connector</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<body style="font-family:system-ui;max-width:40rem;margin:3rem auto;padding:0 1rem;line-height:1.6">
<h1>MidFlight</h1>
<p>Keeps your team's coding agents aligned. Add this connector to your coding client and
sign in with GitHub:</p>
<pre style="background:#f4f4f4;padding:.75rem;overflow-x:auto">{url}</pre>
<p><b>Claude Code</b>: <code>claude mcp add --transport http midflight {url}</code><br>
<b>Codex</b>: <code>codex mcp add midflight --url {url}</code> then
<code>codex mcp login midflight</code><br>
<b>Claude or ChatGPT</b>: add a custom connector with the URL above.</p>
<p>Then tell your agent: <i>“create a MidFlight project called Food app”</i> and share the
join code, or <i>“join MidFlight project MF-XXXX-XXXX as payments”</i>.</p>
</body>"""


def create_app(
    public_url,
    registry,
    service_for,
    *,
    github_sign_in=None,
    dev_login=False,
    health=None,
):
    """The ASGI app: `/mcp`, sign-in, a landing page and `/healthz`."""
    from midflight.api.oauth import MidflightOAuth, add_sign_in_routes

    public_url = public_url.rstrip("/")
    oauth = MidflightOAuth(registry, registry, public_url, github_sign_in, dev_login)
    auth = AuthSettings(
        issuer_url=public_url,
        resource_server_url=f"{public_url}/mcp",
        validate_token_resource=True,  # refuse tokens issued for any other server
        client_registration_options=ClientRegistrationOptions(enabled=True),
        revocation_options=RevocationOptions(enabled=True),
    )
    server = build_hosted_server(registry, service_for, auth=auth, oauth=oauth)
    add_sign_in_routes(server, oauth, github_sign_in)

    @server.custom_route("/healthz", methods=["GET"])
    async def healthz(_request: Request) -> Response:
        try:
            (health or registry.store.read)()
        except Exception:
            return JSONResponse({"detail": "Coordination storage unavailable"}, status_code=503)
        return JSONResponse({"status": "ok"}, headers={"Cache-Control": "no-store"})

    @server.custom_route("/", methods=["GET"])
    async def landing(_request: Request) -> Response:
        return HTMLResponse(_landing(public_url))

    # Stateless JSON responses: any server instance (or Lambda) can answer any request.
    app = server.streamable_http_app(
        stateless_http=True, json_response=True, transport_security=_allowed_hosts(public_url)
    )
    return _without_event_stream(app)


class Services:
    """One coordination Service per project, created on first use and then reused."""

    def __init__(self, store_factory):
        self.store_factory = store_factory
        self.services = {}
        self.lock = threading.Lock()

    def __call__(self, project_id):
        with self.lock:
            if project_id not in self.services:
                store = self.store_factory("hosted_" + project_id)
                self.services[project_id] = Service(store, claim_unowned=True)
            return self.services[project_id]


def _unconfigured_app():
    """Before the first deploy knows its own URL: healthy, but explains what's missing."""

    async def app(scope, receive, send):
        if scope["type"] == "lifespan":
            while True:
                message = await receive()
                if message["type"] == "lifespan.startup":
                    await send({"type": "lifespan.startup.complete"})
                elif message["type"] == "lifespan.shutdown":
                    await send({"type": "lifespan.shutdown.complete"})
                    return
        if scope["path"] == "/healthz":
            response = JSONResponse({"status": "ok", "configured": False})
        else:
            response = JSONResponse(
                {"detail": "MidFlight connector not configured: set MIDFLIGHT_PUBLIC_URL"},
                status_code=503,
            )
        await response(scope, receive, send)

    return app


def create_app_from_env():
    """Production and local entry point, configured by environment variables.

    MIDFLIGHT_PUBLIC_URL     where people reach this server (its own HTTPS URL)
    MIDFLIGHT_DEV_LOGIN=1    a local sign-in form instead of GitHub (never in production)
    MIDFLIGHT_GITHUB_CLIENT_ID / MIDFLIGHT_GITHUB_CLIENT_SECRET   Sign in with GitHub
    MIDFLIGHT_HOSTED_STORE   falkordb (default) or memory
    MIDFLIGHT_DB_HOST / MIDFLIGHT_DB_PORT   the FalkorDB server
    """
    public_url = os.environ.get("MIDFLIGHT_PUBLIC_URL", "").rstrip("/")
    if not public_url:
        return _unconfigured_app()
    dev_login = os.environ.get("MIDFLIGHT_DEV_LOGIN") == "1"
    github_sign_in = None
    client_id = os.environ.get("MIDFLIGHT_GITHUB_CLIENT_ID")
    client_secret = os.environ.get("MIDFLIGHT_GITHUB_CLIENT_SECRET")
    if client_id and client_secret:
        from midflight.adapters.github import GitHubAppSignIn

        github_sign_in = GitHubAppSignIn(client_id, client_secret)
    if os.environ.get("MIDFLIGHT_HOSTED_STORE", "falkordb") == "memory":
        registry, services = memory_backend()
    else:
        registry, services = falkor_backend(
            os.environ.get("MIDFLIGHT_DB_HOST", "127.0.0.1"),
            int(os.environ.get("MIDFLIGHT_DB_PORT", "6379")),
        )
    return create_app(
        public_url, registry, services, github_sign_in=github_sign_in, dev_login=dev_login
    )


def falkor_backend(host, port, prefix=""):
    """Graphs: `hosted_registry`, `hosted_auth`, and `hosted_<project id>` per project."""
    from falkordb import FalkorDB

    from .store import Store

    def store_factory(graph):
        return Store(prefix + graph, port, host=host)

    auth = FalkorAuth(FalkorDB(host=host, port=port).select_graph(prefix + "hosted_auth"))
    return Registry(store_factory("hosted_registry"), auth), Services(store_factory)


def memory_backend():
    from .memory_store import MemoryStore

    return Registry(MemoryStore(), MemoryAuth()), Services(lambda _graph: MemoryStore())
