"""Self-serve projects for the hosted connector, persisted through store CAS.

Anyone signed in can create a project and share its join code. Teammates on other
computers join with that code. Inside a project, an agent name belongs to the member
who first joined with it, so nobody else can speak as that agent. One person may run
several agents under different names.

The registry is one CAS-protected JSON document (like the invite registry). Sign-in
codes and tokens live separately in `AuthRecords`, stored only under their SHA-256 hash.
"""

import json
import re
import secrets
import threading
import time
import uuid
from dataclasses import dataclass

AGENT_NAME = re.compile(r"[A-Za-z0-9_-]{1,60}")
JOIN_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O or 1/I mix-ups
JOIN_CODE = re.compile(r"MF-[A-Z2-9]{4}-[A-Z2-9]{4}")


@dataclass(frozen=True)
class SignedIn:
    """What the sign-in flow needs back: the stable user id it puts in tokens."""

    id: str
    login: str


def new_join_code():
    pick = "".join(secrets.choice(JOIN_ALPHABET) for _ in range(8))
    return f"MF-{pick[:4]}-{pick[4:]}"


def normalized_code(value):
    """Accept a code however it was typed: any case, with or without MF, dashes or spaces."""
    raw = re.sub(r"[^A-Za-z0-9]", "", str(value)).upper()
    if len(raw) == 10 and raw.startswith("MF"):
        raw = raw[2:]
    if len(raw) != 8 or any(c not in JOIN_ALPHABET for c in raw):
        raise ValueError("That isn't a MidFlight join code; it looks like MF-XXXX-XXXX")
    return f"MF-{raw[:4]}-{raw[4:]}"


class Registry:
    def __init__(self, store, auth, clock=time.time):
        self.store = store
        self.auth = auth
        self.clock = clock

    # Persistence --------------------------------------------------------------------------

    def _mutate(self, action):
        for _ in range(50):
            revision, state = self.store.read()
            for key in ("users", "github_ids", "projects", "join_codes", "sessions"):
                state.setdefault(key, {})
            result = action(state)
            if self.store.commit(revision, state):
                return result
        raise RuntimeError("MidFlight is busy; retry the same request")

    def _state(self):
        state = self.store.read()[1]
        for key in ("users", "github_ids", "projects", "join_codes", "sessions"):
            state.setdefault(key, {})
        return state

    # Sign-in (used by midflight.api.oauth.MidflightOAuth) ----------------------------------

    def sign_in(self, account):
        """The MidFlight user for this GitHub account, created on first sign-in."""

        def action(state):
            uid = state["github_ids"].get(str(account.id)) or f"u-{account.id}"
            user = state["users"].setdefault(
                uid, {"github_id": account.id, "created_at": int(self.clock())}
            )
            # People can rename their GitHub account; keep the login current.
            user["login"], user["name"] = account.login, account.name
            state["github_ids"][str(account.id)] = uid
            return SignedIn(uid, account.login)

        return self._mutate(action)

    def get_auth(self, kind, key):
        return self.auth.get(kind, key)

    def put_auth(self, kind, key, value, expires_at=None):
        self.auth.put(kind, key, value, expires_at)

    def delete_auth(self, kind, key):
        self.auth.delete(kind, key)

    # People and projects ------------------------------------------------------------------

    @staticmethod
    def _user(state, uid):
        user = state["users"].get(uid or "")
        if user is None:
            raise ValueError("You aren't signed in to MidFlight; reconnect the connector")
        return user

    @staticmethod
    def _member(state, uid, project_id):
        project = state["projects"].get(project_id or "")
        if project is None or uid not in project["members"]:
            raise ValueError("You aren't a member of that project; check my_projects")
        return project

    def _lead(self, state, uid, project_id):
        project = self._member(state, uid, project_id)
        if project["lead"] != uid:
            raise ValueError("Only the project's lead can do this")
        return project

    def _login(self, state, uid):
        return state["users"].get(uid, {}).get("login", uid)

    def _view(self, state, uid, project):
        return {
            "project_id": project["id"],
            "name": project["name"],
            "role": "lead" if project["lead"] == uid else "member",
            "join_code": project["join_code"],
            "lead": self._login(state, project["lead"]),
            "members": sorted(self._login(state, m) for m in project["members"]),
            "agents": {
                name: self._login(state, owner) for name, owner in sorted(project["agents"].items())
            },
            "retired_agents": sorted(project.get("retired", {})),
        }

    def create_project(self, uid, name):
        name = " ".join(str(name).split())
        if not 1 <= len(name) <= 80:
            raise ValueError("Give the project a name of 1–80 characters")

        def action(state):
            self._user(state, uid)
            code = new_join_code()
            while code in state["join_codes"]:
                code = new_join_code()
            project_id = "p_" + uuid.uuid4().hex[:16]
            state["projects"][project_id] = {
                "id": project_id,
                "name": name,
                "lead": uid,
                "join_code": code,
                "created_at": int(self.clock()),
                "members": {uid: {"joined_at": int(self.clock())}},
                "agents": {},
            }
            state["join_codes"][code] = project_id
            return self._view(state, uid, state["projects"][project_id])

        return self._mutate(action)

    def join_project(self, uid, join_code):
        code = normalized_code(join_code)

        def action(state):
            self._user(state, uid)
            project_id = state["join_codes"].get(code)
            if project_id is None:
                raise ValueError("No project has that join code; ask your lead for the current one")
            project = state["projects"][project_id]
            if uid in project.get("removed", {}):
                raise ValueError("The lead removed you from this project")
            project["members"].setdefault(uid, {"joined_at": int(self.clock())})
            return self._view(state, uid, project)

        return self._mutate(action)

    def projects_of(self, uid):
        state = self._state()
        self._user(state, uid)
        mine = [p for p in state["projects"].values() if uid in p["members"]]
        return [self._view(state, uid, p) for p in sorted(mine, key=lambda p: p["created_at"])]

    def project_for(self, uid, project_id=None):
        """The project a tool call means: the one named, or the caller's only project."""
        state = self._state()
        self._user(state, uid)
        if project_id:
            return self._view(state, uid, self._member(state, uid, project_id))
        mine = [p for p in state["projects"].values() if uid in p["members"]]
        if not mine:
            raise ValueError(
                "You aren't in a project yet: create one with create_project, "
                "or join a teammate's with join_project and their join code"
            )
        if len(mine) > 1:
            listed = ", ".join(f"{p['name']} ({p['id']})" for p in mine)
            raise ValueError(f"You're in several projects; pass project_id. Yours: {listed}")
        return self._view(state, uid, mine[0])

    def rotate_join_code(self, uid, project_id):
        def action(state):
            project = self._lead(state, uid, project_id)
            state["join_codes"].pop(project["join_code"], None)
            code = new_join_code()
            while code in state["join_codes"]:
                code = new_join_code()
            project["join_code"] = code
            state["join_codes"][code] = project["id"]
            return self._view(state, uid, project)

        return self._mutate(action)

    def _target(self, state, project, login):
        target = next(
            (m for m in project["members"] if self._login(state, m).lower() == login.lower()),
            None,
        )
        if target is None:
            raise ValueError(f"{login} isn't a member of this project")
        return target

    def remove_member(self, uid, project_id, login):
        def action(state):
            project = self._lead(state, uid, project_id)
            target = self._target(state, project, login)
            if target == project["lead"]:
                raise ValueError("The lead can't remove themselves")
            del project["members"][target]
            project.setdefault("removed", {})[target] = int(self.clock())
            # Their agents keep their topics, subscriptions and messages, so a name is never
            # free for the taking: the lead hands it to whoever continues that component.
            retired = sorted(n for n, owner in project["agents"].items() if owner == target)
            for name in retired:
                project.setdefault("retired", {})[name] = project["agents"].pop(name)
            return self._view(state, uid, project) | {
                "retired_now": retired,
                "next": "Hand a retired agent to a teammate with assign_agent if someone "
                "continues that component.",
            }

        return self._mutate(action)

    def readmit_member(self, uid, project_id, login):
        """Lead only: let a removed member join again with the join code."""

        def action(state):
            project = self._lead(state, uid, project_id)
            removed = project.setdefault("removed", {})
            target = next(
                (m for m in removed if self._login(state, m).lower() == login.lower()), None
            )
            if target is None:
                raise ValueError(f"{login} wasn't removed from this project")
            del removed[target]
            return self._view(state, uid, project) | {
                "next": f"{login} can join_project with the join code again."
            }

        return self._mutate(action)

    # Agents and sessions ------------------------------------------------------------------

    @staticmethod
    def _valid_name(name):
        if not isinstance(name, str) or not AGENT_NAME.fullmatch(name):
            raise ValueError("Use an agent name of letters, digits, - or _ (up to 60)")

    @staticmethod
    def _case_clash(project, name):
        """Names differing only by case would read as the same agent; refuse them."""
        taken = [*project["agents"], *project.get("retired", {})]
        return next((n for n in taken if n.lower() == name.lower() and n != name), None)

    def bind_agent(self, uid, project_id, name):
        """Reserve an agent name for this member, or confirm it is already theirs."""
        self._valid_name(name)

        def action(state):
            project = self._member(state, uid, project_id)
            if name in project.get("retired", {}):
                raise ValueError(
                    f"The agent {name} belonged to a member who was removed; the lead can "
                    "hand it to you with assign_agent, or pick a different name"
                )
            clash = self._case_clash(project, name)
            if clash:
                raise ValueError(f"This project already has an agent named {clash}")
            owner = project["agents"].setdefault(name, uid)
            if owner != uid:
                raise ValueError(
                    f"In this project the agent name {name} belongs to "
                    f"{self._login(state, owner)}; pick a different name for your component"
                )
            return {"agent": name}

        return self._mutate(action)

    def assign_agent(self, uid, project_id, name, login):
        """Lead only: give an agent name (retired, free or in use) to a member."""
        self._valid_name(name)

        def action(state):
            project = self._lead(state, uid, project_id)
            target = self._target(state, project, login)
            clash = self._case_clash(project, name)
            if clash:
                raise ValueError(f"This project already has an agent named {clash}")
            project.get("retired", {}).pop(name, None)
            previous = project["agents"].get(name)
            project["agents"][name] = target
            return self._view(state, uid, project) | {
                "agent": name,
                "previous": self._login(state, previous) if previous else None,
            }

        return self._mutate(action)

    def agent_holder(self, project_id, name):
        """The member who currently runs this agent, or None (free or retired)."""
        project = self._state()["projects"].get(project_id, {})
        return project.get("agents", {}).get(name)

    def record_session(self, uid, project_id, agent, session_id):
        def action(state):
            old = state["sessions"].setdefault(
                session_id, {"project": project_id, "agent": agent, "user": uid}
            )
            if old != {"project": project_id, "agent": agent, "user": uid}:
                raise ValueError("That session belongs to someone else")
            return {}

        return self._mutate(action)

    def session(self, uid, session_id):
        """(project_id, agent) for a session the caller may still use."""
        state = self._state()
        self._user(state, uid)
        record = state["sessions"].get(session_id or "")
        if record is None or record["user"] != uid:
            raise ValueError("Unknown session; call join first and use the session_id it returns")
        project = self._member(state, uid, record["project"])
        if project["agents"].get(record["agent"]) != uid:
            raise ValueError("The lead gave this agent to someone else; join with another name")
        return record["project"], record["agent"]

    def lead_login(self, uid, project_id):
        """The caller's login, if they lead this project; otherwise refuse."""
        state = self._state()
        self._user(state, uid)
        self._lead(state, uid, project_id)
        return self._login(state, uid)


class MemoryAuth:
    """Sign-in records for tests and local runs; the hosted service uses FalkorAuth."""

    def __init__(self, clock=time.time):
        self.records, self.clock, self.lock = {}, clock, threading.Lock()

    def put(self, kind, key, value, expires_at=None):
        with self.lock:
            self.records[(kind, key)] = (json.dumps(value), expires_at)

    def get(self, kind, key):
        with self.lock:
            found = self.records.get((kind, key))
        if found is None or (found[1] is not None and found[1] < self.clock()):
            return None
        return json.loads(found[0])

    def delete(self, kind, key):
        with self.lock:
            self.records.pop((kind, key), None)


class FalkorAuth:
    """One node per sign-in record, keyed by kind and hash, so tokens never contend."""

    def __init__(self, graph, clock=time.time):
        from redis.exceptions import ResponseError

        self.graph, self.clock = graph, clock
        try:
            self.graph.query("CREATE INDEX ON :HAuth(key)")
        except ResponseError as exc:
            if "already indexed" not in str(exc):
                raise

    def put(self, kind, key, value, expires_at=None):
        self.graph.query(
            "MERGE (a:HAuth {key:$key}) SET a.payload=$payload, a.expires=$expires",
            {"key": json.dumps([kind, key]), "payload": json.dumps(value), "expires": expires_at},
        )
        # Keep the graph small: expired codes and tokens are useless.
        self.graph.query(
            "MATCH (a:HAuth) WHERE a.expires IS NOT NULL AND a.expires < $now DELETE a",
            {"now": self.clock()},
        )

    def get(self, kind, key):
        rows = self.graph.query(
            "MATCH (a:HAuth {key:$key}) WHERE a.expires IS NULL OR a.expires >= $now "
            "RETURN a.payload",
            {"key": json.dumps([kind, key]), "now": self.clock()},
        ).result_set
        return json.loads(rows[0][0]) if rows else None

    def delete(self, kind, key):
        self.graph.query("MATCH (a:HAuth {key:$key}) DELETE a", {"key": json.dumps([kind, key])})
