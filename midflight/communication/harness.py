"""Reviewer-free delivery scenario using the existing four-terminal transport."""

import argparse
import json
import secrets
import socket
import subprocess
import threading
import uuid
from pathlib import Path
from types import SimpleNamespace

import uvicorn
from fastapi.responses import HTMLResponse

from midflight.theater.delivery_fixture import PROMPTS, initial_plan, write_starter
from midflight.theater.interactive import InteractiveTheater, terminal_app
from midflight.theater.peers import PeerTheater

from .mcp import INSTRUCTIONS
from .service import Service
from .store import Store

DEPENDENCIES = {
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


class CommunicationTheater(InteractiveTheater):
    names = tuple(PROMPTS)
    submit_initial_prompt = False
    coordination_tools = ["join", "send", "check_in", "agree"]
    mcp_module = "midflight.communication.mcp"
    first_pane_title = "Billing"

    def __init__(self, root, db_port=6379, api_port=8928, controller_port=8927):
        root = Path(root).resolve()
        root.mkdir(parents=True, exist_ok=False, mode=0o700)
        repo = Path(__file__).resolve().parents[2]
        project = "communication-" + uuid.uuid4().hex
        self.store = Store(project, db_port)
        self.service = Service(self.store)
        self.theater = SimpleNamespace(
            root=root,
            repo=repo,
            project=project,
            db_port=db_port,
            api_port=api_port,
            tokens={name: secrets.token_urlsafe(24) for name in self.names},
            commit=subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=repo, text=True
            ).strip(),
            close=self.store.close,
        )
        self.session = "midflight-" + uuid.uuid4().hex[:8]
        self.key = secrets.token_urlsafe(24)
        self.panes, self.events = {}, []
        self.guard = threading.RLock()
        self.stop_event, self.checkpoint_wake = threading.Event(), threading.Event()
        self.poller = None
        self.controller_port = controller_port
        self.direction = None
        self.version = 1
        self.cues, self.check_ins = {}, {}
        requirements = initial_plan().requirements
        for name in self.names:
            self.service.join(name, PROMPTS[name], "seed", dependencies=DEPENDENCIES[name])
            folder = root / name
            folder.mkdir()
            write_starter(folder, name)
            readme = (
                (folder / "README.md")
                .read_text()
                .replace("in your claim before implementation", "in a message to affected peers")
            )
            (folder / "README.md").write_text(readme)
            own = [
                r
                for r in requirements
                if r.id == name
                or (name in {"billing", "delivery"} and r.id == "cancellation-policy")
            ]
            (folder / "TASK.md").write_text(
                "\n".join([PROMPTS[name]] + [item for r in own for item in r.acceptance_criteria])
                + "\n"
            )
            (folder / "AGENTS.md").write_text(
                f"You are {name}. Read TASK.md and inspect your starter code.\n"
                f"Own only {name}.py and your new component tests. Stay in this workspace.\n"
                "Use theater_midflight for coordination. Do not commit, push or delegate.\n"
                "Join with your name and a fresh request ID. "
                "Existing topic subscriptions are seeded.\n"
                "Do useful local work while a peer is busy; finish the turn if waiting.\n"
                + INSTRUCTIONS
            )
            subprocess.run(["git", "init", "-q", "-b", name], cwd=folder, check=True)
            subprocess.run(["git", "add", "."], cwd=folder, check=True)
            subprocess.run(
                [
                    "git",
                    "-c",
                    "user.name=Demo",
                    "-c",
                    "user.email=demo@localhost",
                    "commit",
                    "-qm",
                    "Preserve incompatible starter",
                ],
                cwd=folder,
                check=True,
            )
        self.service.configure_interfaces(OWNERS)
        (root / "run.json").write_text(
            json.dumps(
                dict(
                    graph=project,
                    db_port=db_port,
                    session=self.session,
                    repo=str(repo),
                    prompts=PROMPTS,
                    controller_port=controller_port,
                ),
                indent=2,
            )
        )
        (root / "prepared-prompts.json").write_text(json.dumps(PROMPTS, indent=2))

    @classmethod
    def restore(cls, root, controller_port=None):
        """Reconnect to a retained run without reseeding or submitting any prompt."""
        root = Path(root).resolve()
        run = json.loads((root / "run.json").read_text())
        metadata = json.loads((root / "interactive.json").read_text())
        live = cls.__new__(cls)
        live.store = Store(run["graph"], run["db_port"])
        live.service = Service(live.store)
        live.theater = SimpleNamespace(
            root=root,
            repo=Path(run["repo"]),
            project=run["graph"],
            db_port=run["db_port"],
            api_port=8928,
            tokens={},
            commit=metadata["commit"],
            close=live.store.close,
        )
        live.session, live.panes = metadata["session"], metadata["panes"]
        live.key = secrets.token_urlsafe(24)
        live.guard = threading.RLock()
        live.stop_event, live.checkpoint_wake = threading.Event(), threading.Event()
        live.poller = None
        live.controller_port = controller_port or run["controller_port"]
        live.direction, live.version = None, 1
        live.cues, live.check_ins, live.events = {}, {}, []
        if subprocess.run(
            ["tmux", "has-session", "-t", live.session], capture_output=True
        ).returncode:
            raise RuntimeError(
                "Saved terminals are absent; retain the run and reset to start new ones"
            )
        return live

    def initial_prompt(self, name, default):
        return PROMPTS[name]

    def plan_tools(self, name):
        return []

    def _checkpoints(self):
        return  # No idle model turns or automatic check-ins.

    def launch(self):
        super().launch()
        PeerTheater.prepare_prompts(self)

    def report(self):
        report = dict(
            project=self.theater.project,
            session=self.session,
            root=str(self.theater.root),
            coordination=self.service.status(),
            integration=None,
        )
        evidence = self.theater.root / "integration.json"
        if evidence.exists():
            report["integration"] = json.loads(evidence.read_text())
        (self.theater.root / "report.json").write_text(json.dumps(report, indent=2))
        return report

    def close(self):
        # Persist full coordination evidence before closing; code and graph are retained.
        self.report()
        (self.theater.root / "ARCHIVED").write_text(
            "Run retained; no reset deletes code or graph.\n"
        )
        super().close()


def app_for(live):
    app = terminal_app(live, factory=CommunicationTheater)
    app.routes.remove(next(r for r in app.routes if getattr(r, "path", None) == "/"))

    @app.get("/")
    def index():
        return HTMLResponse(Path(__file__).with_name("terminal.html").read_text())

    return app


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=18937)
    parser.add_argument("--db-port", type=int, default=6379)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--scenario", choices=["delivery"], default="delivery")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.root is None:
        if args.resume:
            parser.error("--resume requires --root")
        args.root = Path(__file__).resolve().parents[2] / "runs" / uuid.uuid4().hex[:12]
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", args.port))
    if args.resume:
        live = CommunicationTheater.restore(args.root, args.port)
    else:
        live = CommunicationTheater(args.root, args.db_port, controller_port=args.port)
        live.launch()
    uvicorn.run(app_for(live), host="127.0.0.1", port=args.port, access_log=False)


if __name__ == "__main__":
    main()
