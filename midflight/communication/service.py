"""Four tools. Human interpretation and implementation belong to coding agents."""

import re
import uuid
from datetime import UTC, datetime

from .store import encoded

KINDS = {
    "intention",
    "message",
    "question",
    "answer",
    "proposal",
    "policy",
    "applied",
    "implementation",
    "verification",
    "dependency",
    "interface",
    "objection",
    "resolve",
    "transfer",
}


def text(value, name, maximum=2000):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"{name} must contain 1–{maximum} characters")
    return value.strip()


def names(values):
    if not isinstance(values, list) or any(not isinstance(v, str) or not v for v in values):
        raise ValueError("Expected a list of nonempty strings")
    return sorted(set(values))


class Service:
    def __init__(self, store):
        self.store = store

    def _mutate(self, action):
        for _ in range(50):
            revision, state = self.store.read()
            for key in ("owners", "interfaces", "objections"):
                state.setdefault(key, {})
            result = action(state, revision)
            if self.store.commit(revision, state):
                return result
        raise RuntimeError("Concurrent writers: retry with the same request ID")

    def configure_interfaces(self, owners):
        """Operator setup, not an agent tool. Assign only unowned interface topics."""

        def action(state, revision):
            for topic, owner in owners.items():
                text(topic, "topic", 120)
                if owner not in state["agents"]:
                    raise ValueError("Interface owner must be a registered agent")
                old = state["owners"].get(topic)
                if old and old["name"] != owner:
                    raise ValueError("Use an explicit owner transfer; setup cannot replace owners")
                state["owners"].setdefault(topic, {"name": owner, "revision": 1})
            return state["owners"]

        return self._mutate(action)

    def _once(self, state, actor, request_id, payload, action):
        key = encoded([actor, text(request_id, "request_id", 120)])
        fingerprint = encoded(payload)
        old = state["requests"].get(key)
        if old:
            if old["payload"] != fingerprint:
                raise ValueError("request_id already used for different input")
            return old["result"] | {"duplicate": True}
        result = action()
        state["requests"][key] = {"payload": fingerprint, "result": result}
        return result | {"duplicate": False}

    def _session(self, state, sid):
        if sid not in state["sessions"]:
            raise ValueError("Unknown session; join first")
        return state["sessions"][sid]

    def _event(self, state, actor, kind, body, recipients, **extra):
        event = dict(
            id=len(state["events"]) + 1,
            author=actor,
            kind=kind,
            body=body,
            recipients=sorted(set(recipients)),
            created_at=datetime.now(UTC).isoformat(),
            **extra,
        )
        state["events"].append(event)
        return event

    def _inbox(self, state, sid, after=None, full=False):
        session = self._session(state, sid)
        actor = session["agent"]
        start = session["cursor"] if after is None else after
        if type(start) is not int or not 0 <= start <= session["cursor"]:
            raise ValueError("after must be a received cursor or zero")
        visible = [e for e in state["events"] if actor == e["author"] or actor in e["recipients"]]
        unread = [e for e in visible if e["id"] > start]
        page = unread[:50]
        cursor = page[-1]["id"] if page else start
        session["cursor"] = max(session["cursor"], cursor)
        proposals = [p for p in state["proposals"].values() if actor in p["participants"]]
        result = dict(
            session_id=sid,
            agent=actor,
            cursor=cursor,
            messages=page,
            more=len(unread) > 50,
            pending_proposals=[p for p in proposals if p["state"] == "proposed"],
            questions=[
                e
                for e in visible
                if e["kind"] == "question"
                and not any(
                    a["kind"] == "answer" and a.get("reply_to") == e["id"] for a in state["events"]
                )
            ],
        )
        # Supersession is not application. Keep every exact revision and its report.
        policies = [e for e in visible if e["kind"] == "policy"]
        latest = {e["topic"]: e["id"] for e in state["events"] if e["kind"] == "policy"}
        delivered_policies = session.setdefault("delivered_policy_ids", [])
        policy_states = []
        for policy in policies:
            applied = [
                e["id"]
                for e in state["events"]
                if e["kind"] == "applied"
                and e.get("reply_to") == policy["id"]
                and e["author"] == actor
            ]
            policy_states.append(
                policy
                | {
                    "superseded_by": (
                        latest[policy["topic"]] if latest[policy["topic"]] != policy["id"] else None
                    ),
                    "applied_report_ids": applied,
                    "previously_delivered": policy["id"] in delivered_policies,
                }
            )
        result["policy_history"] = policy_states
        result["unapplied_policies"] = [
            p for p in policy_states if p["superseded_by"] is None and not p["applied_report_ids"]
        ]
        # These bodies are included in this response, independently of message pagination.
        session["delivered_policy_ids"] = sorted(
            set(delivered_policies + [p["id"] for p in policies])
        )
        # Current shared interfaces are context, including for a newly subscribed session.
        # Delivery is recorded per session; it never implies agreement or code adoption.
        relevant_topics = set()
        pending = list(state["agents"][actor]["dependencies"])
        while pending:
            topic = pending.pop()
            if topic not in relevant_topics:
                relevant_topics.add(topic)
                pending.extend(state["dependencies"].get(topic, []))
        owners = {
            topic: owner
            for topic, owner in state["owners"].items()
            if owner["name"] == actor or topic in relevant_topics
        }
        delivered = session.setdefault("delivered_interface_revisions", {})
        interfaces = []
        for topic in owners:
            current = state["interfaces"].get(topic)
            if current is not None:
                interfaces.append(
                    current
                    | {
                        "owner": owners[topic]["name"],
                        "previously_delivered_revision": delivered.get(topic, 0),
                    }
                )
                delivered[topic] = current["revision"]
        result["interface_owners"] = state["owners"]
        result["interfaces"] = interfaces
        result["open_objections"] = [
            objection
            for objection in state["objections"].values()
            if objection["state"] == "open"
            and (
                objection["topic"] in owners
                or actor == objection["author"]
                or actor in objection["recipients"]
            )
        ]
        if full:
            result["agreements"] = [p for p in proposals if p["state"] == "agreed"]
            result["policies"] = [e for e in visible if e["kind"] == "policy"]
            result["intentions"] = [e for e in visible if e["kind"] == "intention"]
        return result

    def join(self, name, task, request_id, session_id=None, dependencies=None):
        name, task = text(name, "name", 60), text(task, "task", 300)
        if not re.fullmatch(r"[A-Za-z0-9_-]+", name):
            raise ValueError("Use an alphanumeric agent name")
        dependencies = None if dependencies is None else names(dependencies)

        def mutate(state, revision):
            def action():
                if session_id and self._session(state, session_id)["agent"] != name:
                    raise ValueError("Session belongs to another agent")
                previous = state["agents"].get(name, {}).get("dependencies", [])
                state["agents"][name] = dict(
                    task=task, dependencies=(previous if dependencies is None else dependencies)
                )
                sid = session_id or str(uuid.uuid4())
                state["sessions"].setdefault(sid, dict(agent=name, cursor=0))
                return {"session_id": sid}

            result = self._once(
                state, name, request_id, ["join", task, session_id, dependencies], action
            )
            return result | {
                "members": state["agents"],
                "updates": self._inbox(state, result["session_id"], 0, True),
            }

        return self._mutate(mutate)

    def check_in(self, session_id, after=None):
        return self._mutate(lambda state, rev: self._inbox(state, session_id, after))

    def send(
        self,
        session_id,
        kind,
        body,
        request_id,
        to=None,
        topic="",
        participants=None,
        reply_to=None,
        expected_revision=None,
        source="",
        depends_on=None,
        new_owner=None,
    ):
        if kind not in KINDS:
            raise ValueError("Unknown message kind")
        body = text(body, "body")
        to, participants = names(to or []), names(participants or [])
        if kind in {"proposal", "policy", "intention", "dependency", "interface", "transfer"}:
            topic = text(topic, "topic", 120)
        if kind == "policy":
            text(source, "verbatim human source", 20000)
        elif source:
            raise ValueError("Only policies have a human source")
        if participants and kind != "proposal":
            raise ValueError("Only proposals have participants")
        if depends_on is not None and kind != "dependency":
            raise ValueError("Use dependency kind to declare topic prerequisites")
        if new_owner is not None and kind != "transfer":
            raise ValueError("new_owner is only for ownership transfer")
        dependencies = names(depends_on or [])
        payload = [
            "send",
            kind,
            body,
            to,
            topic,
            participants,
            reply_to,
            expected_revision,
            source,
            dependencies,
        ]

        if new_owner is not None:
            payload.append(new_owner)

        def mutate(state, revision):
            actor = self._session(state, session_id)["agent"]

            def action():
                if not set(to + participants) <= state["agents"].keys():
                    raise ValueError("Unknown recipient or participant; join first")
                routed = self.store.recipients(revision, [topic])
                if topic and to:
                    raise ValueError(
                        "Topic updates route to all dependency subscribers; omit to. "
                        "Use a topic-free direct message for named peers"
                    )
                recipients = to or routed
                current = 0
                owner = state["owners"].get(topic)
                if kind in {"interface", "transfer"}:
                    if owner is None:
                        raise ValueError(
                            "No assigned owner; share an intention and ask the operator "
                            "to assign one"
                        )
                    if actor != owner["name"]:
                        raise ValueError(
                            "Only the interface owner may publish or transfer; send an objection"
                        )
                    if to:
                        raise ValueError(
                            "Interface publications and transfers route to all subscribers; omit to"
                        )
                    recipients = sorted(set(routed + [actor]))
                if kind == "transfer":
                    if new_owner not in state["agents"] or new_owner == actor:
                        raise ValueError("Transfer requires a different registered new_owner")
                    if expected_revision != owner["revision"]:
                        raise ValueError(
                            f"Stale ownership; current revision is {owner['revision']}"
                        )
                    current = owner["revision"] + 1
                    recipients = sorted(set(recipients + [new_owner]))
                if kind in {"proposal", "policy", "dependency", "interface"}:
                    current = max(
                        (
                            e.get("revision", 0)
                            for e in state["events"]
                            if e["kind"] == kind and e.get("topic") == topic
                        ),
                        default=0,
                    )
                    if (expected_revision or 0) != current:
                        raise ValueError(f"Stale {kind}; current revision is {current}")
                    current += 1
                if kind == "proposal":
                    if actor not in participants or len(participants) < 2:
                        raise ValueError("Proposal needs author and at least one peer")
                    recipients = participants
                if kind in {"answer", "applied", "objection", "resolve"} and reply_to is None:
                    raise ValueError("reply_to is required")
                if reply_to is not None:
                    parent = next((e for e in state["events"] if e["id"] == reply_to), None)
                    if parent is None or not (
                        actor in [parent["author"], *parent["recipients"]]
                        or (
                            parent["kind"] in {"interface", "objection"}
                            and state["owners"].get(parent["topic"], {}).get("name") == actor
                        )
                        or (
                            parent["kind"] == "interface"
                            and actor in self.store.recipients(revision, [parent["topic"]])
                        )
                    ):
                        raise ValueError("Unknown or invisible reply target")
                    if kind == "answer" and (
                        parent["kind"] != "question" or actor not in parent["recipients"]
                    ):
                        raise ValueError("Only recipients can answer a question")
                    if kind == "applied" and parent["kind"] != "policy":
                        raise ValueError("Applied reports reference a policy")
                    if kind == "objection":
                        if parent["kind"] != "interface":
                            raise ValueError(
                                "Objection must reference an exact published interface event"
                            )
                        if topic and topic != parent["topic"]:
                            raise ValueError("Objection topic must match its interface")
                        if to:
                            raise ValueError(
                                "Objections route to the owner and subscribers; omit to"
                            )
                        recipients = sorted(
                            set(
                                self.store.recipients(revision, [parent["topic"]])
                                + [actor, state["owners"][parent["topic"]]["name"]]
                            )
                        )
                    if kind == "resolve":
                        objection = state["objections"].get(str(reply_to))
                        if not objection or objection["author"] != actor:
                            raise ValueError(
                                "Only the objection author can resolve it with evidence"
                            )
                        if objection["state"] != "open":
                            raise ValueError("Objection is already resolved")
                        if to:
                            raise ValueError("Resolution reaches the objection audience; omit to")
                    audience = set(parent["recipients"] + [parent["author"]])
                    if parent["kind"] == "objection":
                        audience.add(state["owners"][parent["topic"]]["name"])
                    if parent.get("topic") and parent["kind"] != "proposal":
                        if to:
                            raise ValueError(
                                "Topic replies cannot expand or narrow their audience; omit to"
                            )
                        if topic and topic != parent["topic"]:
                            raise ValueError("Reply topic must match its parent")
                        if kind not in {"interface", "transfer", "policy", "dependency"}:
                            # Replies retain the original relevant audience. New publications
                            # always use the current graph, even when linked to an older event.
                            audience.update(self.store.recipients(revision, [parent["topic"]]))
                    if (
                        not to
                        and (not topic or parent.get("topic"))
                        and kind
                        not in {
                            "objection",
                            "interface",
                            "transfer",
                            "policy",
                            "dependency",
                        }
                    ):
                        recipients = sorted(audience)
                    if kind == "answer" and parent["author"] not in recipients:
                        raise ValueError("Answer must reach question author")
                if not recipients and not topic:
                    raise ValueError(
                        "Supply recipients or a subscribed topic; no broadcast default"
                    )
                if kind == "dependency":
                    state["dependencies"][topic] = dependencies

                    def visit(node, path):
                        if node in path:
                            raise ValueError("Dependency cycle")
                        if len(path) > 32:
                            raise ValueError("Dependency path exceeds 32 edges")
                        for dep in state["dependencies"].get(node, []):
                            visit(dep, path | {node})

                    for node in state["dependencies"]:
                        visit(node, set())
                event = self._event(
                    state,
                    actor,
                    kind,
                    body,
                    recipients,
                    topic=(parent["topic"] if reply_to is not None and not topic else topic),
                    revision=current,
                    reply_to=reply_to,
                    source=source,
                    depends_on=dependencies,
                )
                if kind == "interface":
                    state["interfaces"][topic] = event.copy()
                if kind == "transfer":
                    event["new_owner"] = new_owner
                    state["owners"][topic] = {"name": new_owner, "revision": current}
                if kind == "objection":
                    event["topic"] = parent["topic"]
                    state["objections"][str(event["id"])] = event | {
                        "interface_revision": parent["revision"],
                        "state": "open",
                        "resolution_id": None,
                    }
                if kind == "resolve":
                    event["topic"] = parent["topic"]
                    objection["state"] = "resolved"
                    objection["resolution_id"] = event["id"]
                if kind == "proposal":
                    for proposal in state["proposals"].values():
                        if proposal["topic"] == topic and proposal["state"] == "proposed":
                            proposal["state"] = "superseded"
                    state["proposals"][str(event["id"])] = event | dict(
                        participants=participants, accepted_by=[], state="proposed"
                    )
                return {"event_id": event["id"], "revision": current, "recipients": recipients}

            result = self._once(state, actor, request_id, payload, action)
            return result | {"updates": self._inbox(state, session_id)}

        return self._mutate(mutate)

    def agree(self, session_id, proposal_id, revision, request_id):
        def mutate(state, rev):
            actor = self._session(state, session_id)["agent"]

            def action():
                proposal = state["proposals"].get(str(proposal_id))
                if (
                    not proposal
                    or proposal["revision"] != revision
                    or proposal["state"] == "superseded"
                ):
                    raise ValueError("Unknown, wrong revision or superseded proposal")
                if actor not in proposal["participants"]:
                    raise ValueError("Only a participant can agree")
                proposal["accepted_by"] = sorted(set(proposal["accepted_by"] + [actor]))
                if (
                    proposal["accepted_by"] == proposal["participants"]
                    and proposal["state"] != "agreed"
                ):
                    for old in state["proposals"].values():
                        if old["topic"] == proposal["topic"] and old["state"] == "agreed":
                            old["state"] = "superseded"
                    proposal["state"] = "agreed"
                    self._event(
                        state,
                        actor,
                        "agreement",
                        "Participants explicitly agreed",
                        proposal["participants"],
                        topic=proposal["topic"],
                        revision=revision,
                        reply_to=proposal_id,
                    )
                return dict(
                    proposal_id=proposal_id, revision=revision, accepted=True, implemented=False
                )

            result = self._once(state, actor, request_id, ["agree", proposal_id, revision], action)
            return result | {
                "current_proposal": state["proposals"][str(proposal_id)],
                "state": state["proposals"][str(proposal_id)]["state"],
                "updates": self._inbox(state, session_id),
            }

        return self._mutate(mutate)

    def status(self):
        return self.store.read()[1]
