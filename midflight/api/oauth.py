"""Sign in with GitHub for the hosted connector (task H-3, decision D17).

What happens when someone adds Midflight to their AI client:

1. The client calls `/mcp` without a token and gets 401, which points it at Midflight's
   sign-in discovery document.
2. The client registers itself (`/register`) and opens `/authorize` in the browser.
3. `authorize()` below remembers that request and sends the browser to Midflight's own
   consent page (or to a local form when the dev login is on). The page names the app and
   where it will send the person back; only a click on Continue, in that browser, goes on
   to GitHub. Cookies bind the GitHub round trip to that browser, so a link to GitHub
   crafted by someone else can't sign the person in to the other party's app.
4. GitHub sends the browser back to `/oauth/github/callback` with a code. Midflight
   trades it for the GitHub account, signs the person in, and sends the browser back to
   the AI client with Midflight's own one-time code.
5. The client trades that code at `/token` for an access token (1 hour) and a refresh
   token (30 days). Every `/mcp` call then carries the access token, and its `subject`
   is the Midflight user id.

The MCP SDK implements the protocol endpoints; this module stores what they need. Codes
and tokens are stored under their SHA-256 hash, never as themselves.
"""

from __future__ import annotations

import hashlib
import hmac
import html
import secrets
import time
from typing import Any
from urllib.parse import urlparse

import anyio
from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    AuthorizeError,
    OAuthAuthorizationServerProvider,
    RefreshToken,
    TokenError,
    construct_redirect_uri,
)
from mcp.server.mcpserver import MCPServer
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse, Response

from midflight.ports import GitHubAccount, GitHubSignIn, Store
from midflight.services.projects import ProjectService

ACCESS_TOKEN_SECONDS = 60 * 60
REFRESH_TOKEN_SECONDS = 30 * 24 * 60 * 60
CODE_SECONDS = 5 * 60
PENDING_SECONDS = 10 * 60
GITHUB_CALLBACK = "/oauth/github/callback"
DEV_LOGIN = "/oauth/dev-login"
CONSENT = "/oauth/consent"
CSRF_COOKIE = "midflight_consent"  # SameSite=Strict: only our own consent form sends it
SIGN_IN_COOKIE = "midflight_signin"  # SameSite=Lax: comes back with GitHub's redirect
NO_FRAMES = {"X-Frame-Options": "DENY", "Content-Security-Policy": "frame-ancestors 'none'"}


def _hash(secret: str) -> str:
    return hashlib.sha256(secret.encode()).hexdigest()


class MidflightOAuth(
    OAuthAuthorizationServerProvider[AuthorizationCode, RefreshToken, AccessToken]
):
    def __init__(
        self,
        store: Store,
        projects: ProjectService,
        public_url: str,
        github: GitHubSignIn | None,
        dev_login: bool = False,
    ) -> None:
        if github is None and not dev_login:
            raise ValueError("configure Sign in with GitHub, or turn on the local dev login")
        self._store = store
        self._projects = projects
        self._public_url = public_url
        self.resource_url = f"{public_url}/mcp"
        self._github = github
        self.dev_login = dev_login

    # Clients (dynamic client registration) ---------------------------------------------

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        data = self._store.get_auth("client", client_id)
        return OAuthClientInformationFull.model_validate(data) if data else None

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        self._store.put_auth(
            "client", client_info.client_id or "", client_info.model_dump(mode="json")
        )

    # Step 3: start signing in ----------------------------------------------------------

    async def authorize(
        self, client: OAuthClientInformationFull, params: AuthorizationParams
    ) -> str:
        pending = secrets.token_urlsafe(24)
        self._store.put_auth(
            "pending",
            _hash(pending),
            {"client_id": client.client_id, "params": params.model_dump(mode="json")},
            time.time() + PENDING_SECONDS,
        )
        if self.dev_login:
            return f"{self._public_url}{DEV_LOGIN}?pending={pending}"
        return f"{self._public_url}{CONSENT}?pending={pending}"

    @property
    def github_redirect_uri(self) -> str:
        return f"{self._public_url}{GITHUB_CALLBACK}"

    @property
    def secure_cookies(self) -> bool:
        return self._public_url.startswith("https://")

    def consent_details(self, pending: str) -> tuple[str, str]:
        """(app name, host it will send the person back to) for a pending sign-in."""
        request = self._store.get_auth("pending", _hash(pending))
        if request is None:
            raise AuthorizeError("access_denied", "this sign-in link expired; start again")
        client = self._store.get_auth("client", request["client_id"]) or {}
        redirect = request["params"]["redirect_uri"]
        host = urlparse(str(redirect)).netloc or str(redirect)
        return str(client.get("client_name") or "An app"), host

    def github_authorize_url(self, pending: str) -> str:
        self.consent_details(pending)  # still pending
        assert self._github is not None
        return self._github.authorize_url(pending, self.github_redirect_uri)

    # Step 4: GitHub (or the dev form) says who signed in --------------------------------

    def finish_sign_in(self, pending: str, account: GitHubAccount) -> str:
        """Sign the person in and return where to send their browser: back to the client."""
        request = self._store.get_auth("pending", _hash(pending))
        if request is None:
            raise AuthorizeError("access_denied", "this sign-in link expired; start again")
        self._store.delete_auth("pending", _hash(pending))
        params = AuthorizationParams.model_validate(request["params"])
        user = self._projects.sign_in(account)
        code = secrets.token_urlsafe(32)
        self._store.put_auth(
            "code",
            _hash(code),
            {
                "client_id": request["client_id"],
                "scopes": params.scopes or [],
                "code_challenge": params.code_challenge,
                "redirect_uri": str(params.redirect_uri),
                "redirect_uri_provided_explicitly": params.redirect_uri_provided_explicitly,
                "resource": params.resource,
                "subject": user.id,
                "expires_at": time.time() + CODE_SECONDS,
            },
            time.time() + CODE_SECONDS,
        )
        return construct_redirect_uri(str(params.redirect_uri), code=code, state=params.state)

    # Step 5: codes and tokens ----------------------------------------------------------

    async def load_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: str
    ) -> AuthorizationCode | None:
        data = self._store.get_auth("code", _hash(authorization_code))
        if data is None or data["client_id"] != client.client_id:
            return None
        return AuthorizationCode(code=authorization_code, **data)

    async def exchange_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: AuthorizationCode
    ) -> OAuthToken:
        self._store.delete_auth("code", _hash(authorization_code.code))  # one use only
        return self._issue(
            client.client_id or "",
            authorization_code.scopes,
            authorization_code.subject,
            authorization_code.resource,
        )

    async def load_refresh_token(
        self, client: OAuthClientInformationFull, refresh_token: str
    ) -> RefreshToken | None:
        data = self._store.get_auth("refresh", _hash(refresh_token))
        if data is None or data["client_id"] != client.client_id:
            return None
        return RefreshToken(token=refresh_token, **data)

    async def exchange_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: RefreshToken,
        scopes: list[str],
    ) -> OAuthToken:
        self._store.delete_auth("refresh", _hash(refresh_token.token))  # rotate it
        return self._issue(
            client.client_id or "",
            scopes or refresh_token.scopes,
            refresh_token.subject,
            refresh_token.resource,
        )

    async def load_access_token(self, token: str) -> AccessToken | None:
        data = self._store.get_auth("access", _hash(token))
        return AccessToken(token=token, **data) if data else None

    async def revoke_token(self, token: AccessToken | RefreshToken) -> None:
        self._store.delete_auth("access", _hash(token.token))
        self._store.delete_auth("refresh", _hash(token.token))

    def _issue(
        self, client_id: str, scopes: list[str], subject: str | None, resource: str | None
    ) -> OAuthToken:
        if subject is None:
            raise TokenError("invalid_grant", "this grant isn't tied to a signed-in person")
        # Every token is for this server's /mcp, even if the client didn't say so.
        resource = resource or self.resource_url
        access, refresh = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        now = int(time.time())
        common: dict[str, Any] = {
            "client_id": client_id,
            "scopes": scopes,
            "subject": subject,
            "resource": resource,
        }
        self._store.put_auth(
            "access",
            _hash(access),
            {**common, "expires_at": now + ACCESS_TOKEN_SECONDS},
            now + ACCESS_TOKEN_SECONDS,
        )
        self._store.put_auth(
            "refresh",
            _hash(refresh),
            {**common, "expires_at": now + REFRESH_TOKEN_SECONDS},
            now + REFRESH_TOKEN_SECONDS,
        )
        return OAuthToken(
            access_token=access,
            expires_in=ACCESS_TOKEN_SECONDS,
            refresh_token=refresh,
            scope=" ".join(scopes) or None,
        )


# Browser pages on the MCP server -------------------------------------------------------


def add_sign_in_routes(
    server: MCPServer, oauth: MidflightOAuth, github: GitHubSignIn | None
) -> None:
    """The pages a browser visits while signing in: GitHub's callback, or the dev form."""

    def cookie(response: Response, name: str, value: str, same_site: str) -> None:
        response.set_cookie(
            name,
            value,
            max_age=PENDING_SECONDS,
            path="/oauth",
            httponly=True,
            secure=oauth.secure_cookies,
            samesite=same_site,  # type: ignore[arg-type]
        )

    @server.custom_route(CONSENT, methods=["GET"])
    async def consent_page(request: Request) -> Response:
        pending = request.query_params.get("pending", "")
        try:
            app_name, host = oauth.consent_details(pending)
        except AuthorizeError as error:
            return _page("Sign-in failed", error.error_description or error.error, 400)
        token = secrets.token_urlsafe(24)
        response = _page(
            "Sign in to Midflight",
            f"{app_name} wants to use Midflight as you, and will receive access at {host}. "
            "Continue only if you just started this from your own coding client.",
            200,
            f'<form method="post"><input type="hidden" name="pending" '
            f'value="{html.escape(pending)}"><input type="hidden" name="csrf" '
            f'value="{token}"><button>Continue with GitHub</button></form>',
        )
        response.headers.update(NO_FRAMES)
        cookie(response, CSRF_COOKIE, token, "strict")
        return response

    @server.custom_route(CONSENT, methods=["POST"])
    async def consent_given(request: Request) -> Response:
        form = await request.form()
        pending, token = str(form.get("pending", "")), str(form.get("csrf", ""))
        expected = request.cookies.get(CSRF_COOKIE, "")
        if not token or not expected or not hmac.compare_digest(token, expected):
            return _page("Sign-in failed", "Open the sign-in link again and press Continue.", 400)
        if github is None:
            return _page("Sign-in failed", "Sign in with GitHub isn't configured here.", 400)
        try:
            target = oauth.github_authorize_url(pending)
        except AuthorizeError as error:
            return _page("Sign-in failed", error.error_description or error.error, 400)
        response = RedirectResponse(target, status_code=302)
        cookie(response, SIGN_IN_COOKIE, _hash(pending), "lax")
        response.delete_cookie(CSRF_COOKIE, path="/oauth")
        return response

    @server.custom_route(GITHUB_CALLBACK, methods=["GET"])
    async def github_callback(request: Request) -> Response:
        code, pending = request.query_params.get("code"), request.query_params.get("state")
        if not code or not pending or github is None:
            return _page(
                "Sign-in failed", "GitHub didn't send back a sign-in code. Try again.", 400
            )
        started_here = request.cookies.get(SIGN_IN_COOKIE, "")
        if not started_here or not hmac.compare_digest(started_here, _hash(pending)):
            return _page(
                "Sign-in failed",
                "This sign-in didn't start in this browser. Start again from your coding client.",
                400,
            )
        try:
            account = await anyio.to_thread.run_sync(
                github.account_for_code, code, oauth.github_redirect_uri
            )
            response = RedirectResponse(oauth.finish_sign_in(pending, account), status_code=302)
            response.delete_cookie(SIGN_IN_COOKIE, path="/oauth")
            return response
        except Exception as error:  # shown to the person, never a stack trace
            return _page("Sign-in failed", str(error), 400)

    if not oauth.dev_login:
        return

    @server.custom_route(DEV_LOGIN, methods=["GET"])
    async def dev_login_form(request: Request) -> Response:
        pending = html.escape(request.query_params.get("pending", ""))
        return _page(
            "Midflight dev login",
            "Local development only: pick the GitHub login to sign in as.",
            200,
            f'<form method="post"><input type="hidden" name="pending" value="{pending}">'
            '<input name="login" placeholder="github login" autofocus required> '
            "<button>Sign in</button></form>",
        )

    @server.custom_route(DEV_LOGIN, methods=["POST"])
    async def dev_login_submit(request: Request) -> Response:
        form = await request.form()
        login = str(form.get("login", "")).strip()
        pending = str(form.get("pending", ""))
        if not login:
            return _page("Sign-in failed", "Enter a login.", 400)
        account = GitHubAccount(id=dev_github_id(login), login=login)
        try:
            return RedirectResponse(oauth.finish_sign_in(pending, account), status_code=302)
        except AuthorizeError as error:
            return _page("Sign-in failed", error.error_description or error.error, 400)


def dev_github_id(login: str) -> int:
    """A stable fake GitHub id for the dev login, far above real GitHub ids."""
    return 10**12 + int(hashlib.sha256(login.lower().encode()).hexdigest()[:8], 16)


def _page(title: str, message: str, status: int, extra: str = "") -> HTMLResponse:
    body = (
        f"<!doctype html><title>{html.escape(title)}</title>"
        '<body style="font-family:system-ui;max-width:32rem;margin:4rem auto">'
        f"<h1>{html.escape(title)}</h1><p>{html.escape(message)}</p>{extra}</body>"
    )
    return HTMLResponse(body, status_code=status)
