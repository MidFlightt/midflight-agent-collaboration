"""Bounded invite redemption and credential registry, persisted through store CAS."""

import hashlib
import hmac
import secrets
import time
import uuid

from .service import Service

AGENTS = {
    "billing": ["delivery-record", "cancellation-policy"],
    "delivery": ["delivery-record", "booking-request", "cancellation-policy"],
    "booking": ["booking-request", "delivery-record"],
    "notifications": ["confirmation"],
}
OWNERS = {
    "delivery-record": "delivery",
    "booking-request": "booking",
    "confirmation": "notifications",
}


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


class Invites:
    def __init__(self, store, signing_key, clock=time.time):
        if len(signing_key) < 32:
            raise ValueError("Invite signing key must contain at least 32 characters")
        self.service = Service(store)
        self.key = signing_key.encode()
        self.clock = clock

        def bind_key(state, revision):
            fingerprint = digest(signing_key)
            if state.setdefault("invite_signing_key_hash", fingerprint) != fingerprint:
                raise ValueError("Invite signing key changed; restore the original key")
            return {}

        self.service._mutate(bind_key)

    def create(self, max_uses, lifetime_hours, access_hours):
        if (
            not 1 <= max_uses <= 50
            or not 1 <= lifetime_hours <= 168
            or not 1 <= access_hours <= 720
        ):
            raise ValueError("Limit invites to 50 uses, 7 days to join, 30 days of access")
        identifier, secret = uuid.uuid4().hex, secrets.token_urlsafe(32)
        now = int(self.clock())
        invite = dict(
            id=identifier,
            mode="sandbox",
            secret_hash=digest(secret),
            max_uses=max_uses,
            expires_at=now + lifetime_hours * 3600,
            access_hours=access_hours,
            revoked=False,
            redemptions={},
        )

        def action(state, revision):
            state.setdefault("invites", {})[identifier] = invite
            return {"id": identifier, "secret": secret, "expires_at": invite["expires_at"]}

        return self.service._mutate(action)

    def _invite(self, state, identifier, secret):
        invite = state.get("invites", {}).get(identifier)
        if not invite or not hmac.compare_digest(invite["secret_hash"], digest(secret)):
            raise PermissionError("Invalid invite")
        if invite["revoked"] or self.clock() >= invite["expires_at"]:
            raise PermissionError("Invite expired or revoked")
        return invite

    def info(self, identifier, secret):
        invite = self._invite(self.service.store.read()[1], identifier, secret)
        return dict(
            mode=invite["mode"],
            expires_at=invite["expires_at"],
            remaining=invite["max_uses"] - len(invite["redemptions"]),
        )

    def _token(self, identifier, request_id, agent):
        return hmac.new(
            self.key, f"{identifier}:{request_id}:{agent}".encode(), hashlib.sha256
        ).hexdigest()

    def redeem(self, identifier, secret, request_id):
        # The random request ID is a recovery secret: only its hash is persisted.
        if len(request_id) < 32 or len(request_id) > 128:
            raise ValueError("Supply a random request ID of 32–128 characters")
        request_hash = digest(request_id)

        def action(state, revision):
            invite = self._invite(state, identifier, secret)
            old = invite["redemptions"].get(request_hash)
            if old:
                if self.clock() >= old["expires_at"]:
                    raise PermissionError("Access expired")
                return old
            if len(invite["redemptions"]) >= invite["max_uses"]:
                raise ValueError("Invite has no remaining places")
            project = "invite_demo_" + uuid.uuid4().hex
            record = dict(
                project=project, expires_at=int(self.clock()) + invite["access_hours"] * 3600
            )
            state.setdefault("projects", {}).setdefault(
                project, {"agents": AGENTS, "owners": OWNERS}
            )
            for name in AGENTS:
                state.setdefault("credentials", {})[
                    digest(self._token(identifier, request_id, name))
                ] = dict(
                    project=project, agent=name, invite=identifier, expires_at=record["expires_at"]
                )
            invite["redemptions"][request_hash] = record
            return record

        record = self.service._mutate(action)
        return dict(
            project=record["project"],
            expires_at=record["expires_at"],
            tokens={a: self._token(identifier, request_id, a) for a in AGENTS},
        )

    def authenticate(self, token):
        state = self.service.store.read()[1]
        identity = state.get("credentials", {}).get(digest(token))
        if not identity or self.clock() >= identity["expires_at"]:
            return None
        if state["invites"][identity["invite"]]["revoked"]:
            return None
        return identity, state["projects"][identity["project"]]

    def revoke(self, identifier):
        def action(state, revision):
            if identifier not in state.get("invites", {}):
                raise ValueError("Unknown invite")
            state["invites"][identifier]["revoked"] = True
            return {"revoked": True}

        return self.service._mutate(action)
