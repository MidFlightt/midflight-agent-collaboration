"""Run the peer experiment separately: python -m midflight.theater.peers."""

import argparse
import json
import os
import re
import socket
import subprocess
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

import uvicorn
from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from midflight.domain.models import Role
from midflight.ports import Commit
from midflight.services.plans import PlanDraft
from midflight.theater.interactive import InteractiveTheater, terminal_app
from midflight.theater.peer_coordination import PeerCoordination
from midflight.theater.scenario import NAMES

TASKS = {
    "pricing": 'Implement pricing.py: price() returns {"total_cents": 1200}.',
    "checkout": "Implement checkout.py: checkout(price) returns an order with total_cents.",
    "reporting": "Implement reporting.py: report(order) returns its total_cents.",
    "notifications": 'Implement notifications.py: notify(email) returns "Subscribed: " + email.',
}


class PeerTheater(InteractiveTheater):
    mcp_module = "midflight.theater.peer_mcp"

    def __init__(self, root, db_port, api_port, controller_port=8907):
        super().__init__(root, db_port, api_port, controller_port)
        store = self.theater.server.services.store
        # Existing domain permissions are reused only in this isolated experimental project.
        store.commit(
            Commit(
                self.theater.project,
                "equal-peer-capabilities",
                puts=[
                    store.get_participant(n).model_copy(update={"role": Role.LEAD}) for n in NAMES
                ],
            )
        )
        self.coordination = PeerCoordination(self.theater.server.services, self.theater.project)
        for name, brief in TASKS.items():
            (self.theater.root / name / "TASK.md").write_text(brief + "\n")

    def initial_prompt(self, name, default):
        return "Build your task in TASK.md. Coordinate with the team through MidFlight."

    def plan_tools(self, name):
        return ["read_shared_plan", "publish_shared_plan"]

    def launch(self):
        super().launch()
        self.tmux("select-pane", "-t", self.panes["pricing"], "-T", "Pricing")

    def set_direction(self, name, direction):
        raise HTTPException(
            422, "Use the peer plan tools; this experiment has no scripted direction"
        )

    def publish(self, name, expected_version, direction, draft):
        with self.guard:
            plan, replayed = self.coordination.publish(name, expected_version, direction, draft)
            self.version, self.direction, self.changed = plan.version, direction, True
            if not replayed:
                self.record(
                    "direction_accepted", name, direction=direction, plan_version=plan.version
                )
                self.checkpoint_wake.set()
            return {
                "plan_version": plan.version,
                "replayed": replayed,
                "changed_ids": plan.changed_ids,
                "next": "Check in for your own task.",
            }

    def _checkpoints(self):
        # Generic wake-up only after a real plan change; never inserts product instructions.
        while not self.stop_event.is_set():
            self.checkpoint_wake.wait(5)
            self.checkpoint_wake.clear()
            if self.version == 1:
                continue
            for name in NAMES:
                if self.stop_event.is_set():
                    return
                key = (self.version, name)
                if self.checkpoint_counts.get(key):
                    continue
                try:
                    tail = "\n".join(
                        self.tmux("capture-pane", "-p", "-t", self.panes[name]).splitlines()[-14:]
                    )
                    if "Ask Codex to do anything" not in tail or re.search(
                        r"esc to interrupt|Starting MCP|Working \(", tail, re.I
                    ):
                        continue
                    self.tmux(
                        "send-keys",
                        "-t",
                        self.panes[name],
                        "-l",
                        "Check MidFlight for updates to your task.",
                    )
                    time.sleep(0.5)
                    self.tmux("send-keys", "-t", self.panes[name], "Enter")
                    self.checkpoint_counts[key] = 1
                except subprocess.CalledProcessError:
                    continue

    def report(self):
        services = self.theater.server.services
        claims = services.store.list_claims(self.theater.project)
        directives = services.store.list_directives(self.theater.project)
        agents = {
            n: {"alive": self.tmux("display-message", "-p", "-t", p, "#{pane_dead}") == "0"}
            for n, p in self.panes.items()
        }
        report = {
            "mode": "peer-experiment",
            "plan_version": self.version,
            "phase": "changed" if self.changed else "initial",
            "human_direction": self.direction,
            "project": self.theater.project,
            "commit": self.theater.commit,
            "dirty": self.theater.dirty,
            "time": datetime.now(UTC).isoformat(),
            "visual_events": self.events,
            "integration": {
                "passed": None,
                "output": "No generic integration oracle configured. Inspect agent test output.",
            },
            "direction": self.direction,
            "session": self.session,
            "checks": {
                "four_claims": {c.task_id for c in claims} == set(NAMES),
                "all_claims_approved": len(claims) >= 4
                and all(c.state.value == "approved" for c in claims),
                "sessions_alive": all(a["alive"] for a in agents.values()),
            },
            "code_tests": "Not assessed. No generic integration oracle configured.",
            "claims": [c.model_dump(mode="json") for c in claims],
            "directives": [d.model_dump(mode="json") for d in directives],
            "events": self.events,
            "agents": agents,
        }
        (self.theater.root / "report.json").write_text(json.dumps(report, indent=2))
        return report


class Update(BaseModel):
    expected_version: int = Field(ge=1)
    direction: str = Field(min_length=1, max_length=4000)
    plan: PlanDraft


def peer_app(live):
    app = terminal_app(live, factory=PeerTheater)

    @app.get("/peer-plan")
    def read(request: Request):
        peer = app.state.live
        name = peer.actor_for(request.headers.get("authorization", ""))
        return peer.coordination.read(name).model_dump(mode="json")

    @app.post("/peer-plan")
    def publish(request: Request, update: Update):
        peer = app.state.live
        name = peer.actor_for(request.headers.get("authorization", ""))
        with app.state.control_lock:
            peer = app.state.live
            name = peer.actor_for(request.headers.get("authorization", ""))
            return peer.publish(name, update.expected_version, update.direction, update.plan)

    # Replace the HTML route while retaining the same terminal transport and reset controls.
    route = next(r for r in app.routes if getattr(r, "path", None) == "/")
    app.routes.remove(route)

    @app.get("/")
    def index():
        html = Path(__file__).with_name("terminal.html").read_text()
        html = html.replace("Pricing / Lead", "any agent").replace(" / Lead", "")
        html = html.replace("Test results</a>", "Coordination</a>")
        html = html.replace("One-off sales · waiting for your direction", "Peer experiment · ready")
        return HTMLResponse(html)

    return app


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8907)
    parser.add_argument("--api-port", type=int, default=8908)
    parser.add_argument("--db-port", type=int, default=6379)
    args = parser.parse_args()
    for port in (args.port, args.api_port):
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", port))
    os.umask(0o077)
    root = Path.home() / ".local/share/midflight-demo" / ("peers-" + uuid.uuid4().hex[:10])
    live = PeerTheater(root, args.db_port, args.api_port, args.port)
    live.launch()
    uvicorn.run(peer_app(live), host="127.0.0.1", port=args.port, access_log=False)


if __name__ == "__main__":
    main()
