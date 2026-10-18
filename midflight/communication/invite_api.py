"""Invite HTTP routes. Link secrets stay in URL fragments, outside HTTP request URLs."""

import hmac
from pathlib import Path

from fastapi import Header, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ConfigDict, Field

from .invites import digest


class InviteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    id: str = Field(pattern=r"^[a-f0-9]{32}$")
    secret: str = Field(min_length=32, max_length=128)


class Redemption(InviteRequest):
    request_id: str = Field(min_length=32, max_length=128)


class NewInvite(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    max_uses: int = Field(default=20, ge=1, le=50)
    lifetime_hours: int = Field(default=168, ge=1, le=168)
    access_hours: int = Field(default=168, ge=1, le=720)


def routes(app, registry, admin_hash):
    def admin(authorization):
        if not authorization.startswith("Bearer ") or not hmac.compare_digest(
            digest(authorization[7:]), admin_hash
        ):
            raise HTTPException(401, "Invalid operator credential")

    def call(action, *args):
        try:
            return action(*args)
        except PermissionError as error:
            raise HTTPException(403, str(error)) from None
        except ValueError as error:
            raise HTTPException(409, str(error)) from None
        except Exception:
            raise HTTPException(
                503, "Invite storage unavailable; retry with the same request ID"
            ) from None

    @app.get("/invite")
    def landing():
        return HTMLResponse(
            Path(__file__).with_name("invite.html").read_text(),
            headers={
                "Cache-Control": "no-store",
                "Referrer-Policy": "no-referrer",
                "Content-Security-Policy": (
                    "default-src 'none'; script-src 'unsafe-inline'; "
                    "style-src 'unsafe-inline'; connect-src 'self'; "
                    "base-uri 'none'; frame-ancestors 'none'"
                ),
            },
        )

    @app.post("/v1/invites/info")
    def info(payload: InviteRequest):
        return call(registry.info, payload.id, payload.secret)

    @app.post("/v1/invites/redeem")
    def redeem(payload: Redemption):
        return call(registry.redeem, payload.id, payload.secret, payload.request_id)

    @app.post("/v1/invites")
    def create(payload: NewInvite, authorization: str = Header(default="")):
        admin(authorization)
        return call(registry.create, payload.max_uses, payload.lifetime_hours, payload.access_hours)

    @app.delete("/v1/invites/{identifier}")
    def revoke(identifier: str, authorization: str = Header(default="")):
        admin(authorization)
        return call(registry.revoke, identifier)
