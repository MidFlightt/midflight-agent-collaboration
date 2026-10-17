"""One real application repo, four peer worktrees, and no seeded interfaces."""

import argparse
import json
import os
import re
import secrets
import subprocess
import threading
import time
import tomllib
import uuid
from pathlib import Path

import uvicorn
from fastapi import Request

from midflight.domain.models import Participant, Project, Requirement, Role, Task
from midflight.ports import Commit
from midflight.services.participants import hash_token, new_token
from midflight.services.plans import PlanDraft
from midflight.theater.app import Theater
from midflight.theater.interactive import InteractiveTheater
from midflight.theater.peer_coordination import PeerCoordination
from midflight.theater.peers import PeerTheater, peer_app

NAMES = ("api", "web", "cli", "docs")
PROMPTS = {
    "api": "Build a Python API for the task board. Coordinate with MidFlight.",
    "web": "Build the task-board web interface. Coordinate with MidFlight.",
    "cli": "Build a CLI for the task board. Coordinate with MidFlight.",
    "docs": "Write setup instructions and an end-to-end smoke test. Coordinate with MidFlight.",
}


def seed_lab(services, project):
    tokens = {name: new_token() for name in NAMES}
    people = [
        Participant(
            id=name,
            project_id=project,
            role=Role.LEAD,
            developer_name=name,
            token_hash=hash_token(token),
        )
        for name, token in tokens.items()
    ]
    services.store.commit(
        Commit(
            project,
            "lab-seed",
            puts=[
                Project(
                    id=project,
                    repository="worktree-lab/task-board",
                    lead_id="api",
                    participant_ids=list(tokens),
                ),
                *people,
            ],
        )
    )
    draft = PlanDraft(
        requirements=[
            Requirement(
                id="task-board",
                description=(
                    "Build a small local task board for creating, listing and completing tasks. "
                    "Use Python's standard library and plain browser HTML/JavaScript."
                ),
            )
        ],
        tasks=[
            Task(
                id=name,
                title=PROMPTS[name],
                owner=name,
                branch="agent-" + name,
                requirement_ids=["task-board"],
            )
            for name in NAMES
        ],
        contracts=[],
    )
    actor = services.store.get_participant("api")
    proposed = services.plans.propose(actor, draft)
    services.plans.approve(
        actor, proposed.version, "Initial task-board assignments; no interfaces yet"
    )
    return tokens


def create_repository(root):
    repository = root / "repository"
    repository.mkdir()
    git = ["git", "-c", "user.name=MidFlight Lab", "-c", "user.email=lab@localhost"]
    subprocess.run([*git, "init", "-q", "-b", "main", str(repository)], check=True)
    subprocess.run(
        ["git", "-C", str(repository), "config", "user.name", "MidFlight Lab"], check=True
    )
    subprocess.run(
        ["git", "-C", str(repository), "config", "user.email", "lab@localhost"], check=True
    )
    (repository / "README.md").write_text(
        "# Task board\n\nBuild a small local app for creating, listing and completing tasks.\n"
        "Python standard library backend; plain HTML/JavaScript frontend.\n"
        "API, web, CLI and documentation agents collaborate through MidFlight.\n"
        "No API shape, file ownership or dependency contracts have been predetermined.\n"
    )
    (repository / ".gitignore").write_text("__pycache__/\n*.pyc\nnode_modules/\n.venv/\n*.db\n")
    subprocess.run([*git, "-C", str(repository), "add", "."], check=True)
    subprocess.run(
        [*git, "-C", str(repository), "commit", "-qm", "Start task-board project"], check=True
    )
    for name in NAMES:
        subprocess.run(
            [
                *git,
                "-C",
                str(repository),
                "worktree",
                "add",
                "-q",
                "-b",
                "agent-" + name,
                str(root / name),
                "main",
            ],
            check=True,
        )
    return repository


def worktree_permissions(root, name):
    """Allow ordinary worktree Git operations without unrestricted filesystem writes."""
    if name not in NAMES:
        raise ValueError("Unknown lab agent")
    filesystem = {
        ":root": "read",
        str((root / name).resolve()): "write",
        str((root / "repository" / ".git").resolve()): "write",
        str((root / "repository" / ".git" / "worktrees" / name).resolve()): "write",
        ":tmpdir": "write",
        ":slash_tmp": "write",
    }
    filesystem.update({str((root / peer).resolve()): "read" for peer in NAMES if peer != name})
    toml = "{" + ",".join(json.dumps(k) + "=" + json.dumps(v) for k, v in filesystem.items()) + "}"
    return [
        "-c",
        'default_permissions="worktree-lab"',
        "-c",
        "permissions.worktree-lab.filesystem=" + toml,
        "-c",
        "permissions.worktree-lab.network.enabled=true",
        "-c",
        "features.network_proxy=false",
    ]


class LabRun(Theater):
    def __init__(self, root, db_port, api_port, *, resume=False):
        metadata = json.loads((root / "interactive.json").read_text()) if resume else None
        tokens = {}
        if resume:
            for name in NAMES:
                args = json.loads((root / (name + "-launch.json")).read_text())
                for index, arg in enumerate(args[:-1]):
                    if arg == "-c" and args[index + 1].startswith("mcp_servers.theater_midflight="):
                        config = tomllib.loads(args[index + 1])
                        tokens[name] = config["mcp_servers"]["theater_midflight"]["env"][
                            "MIDFLIGHT_TOKEN"
                        ]
            if set(tokens) != set(NAMES):
                raise ValueError("Missing private launch credentials for resume")
        super().__init__(
            root,
            db_port,
            api_port,
            seed_fn=seed_lab,
            prepare_workspaces=False,
            existing_project=metadata["project"] if metadata else None,
            existing_tokens=tokens if resume else None,
        )
        self.repository = self.root / "repository" if resume else create_repository(self.root)


class WorktreeLab(PeerTheater):
    names = NAMES
    mcp_module = "midflight.theater.worktree_mcp"

    def __init__(self, root, db_port, api_port, controller_port=8937, *, resume=False):
        self.theater = LabRun(root, db_port, api_port, resume=resume)
        self.session = "midflight-lab-" + uuid.uuid4().hex[:8]
        self.key = secrets.token_urlsafe(24)
        self.panes = {}
        self.changed = False
        self.controller_port = controller_port
        self.viewer_url = f"http://127.0.0.1:{controller_port + 10}/"
        self.direction = None
        self.cues = dict.fromkeys(self.names, "unchanged")
        self.check_ins = dict.fromkeys(self.names, 0)
        self.events = []
        self.guard = threading.RLock()
        self.stop_event = threading.Event()
        self.checkpoint_wake = threading.Event()
        self.poller = None
        self.checkpoint_counts = {}
        self.version = 1
        self.coordination = PeerCoordination(
            self.theater.server.services,
            self.theater.project,
            names=self.names,
            preserve_tasks=False,
        )
        if resume:
            metadata = json.loads((root / "interactive.json").read_text())
            report = json.loads((root / "report.json").read_text())
            self.session, self.panes = metadata["session"], metadata["panes"]
            self.version = self.coordination.read(self.names[0]).version
            self.events = report.get("events", [])
            self.direction = report.get("direction")
            self.changed = self.version > 1
            self.poller = threading.Thread(target=self._checkpoints, daemon=True)
            self.poller.start()

    def initial_prompt(self, name, default):
        return PROMPTS[name]

    def permission_args(self, name):
        return worktree_permissions(self.theater.root, name)

    def plan_tools(self, name):
        return ["read_shared_plan", "publish_shared_plan", "team_branches"]

    def launch(self):
        InteractiveTheater.launch(self)

    def team_branches(self):
        result = []
        for name in self.names:
            workspace = self.theater.root / name

            def git(*args, cwd=workspace):
                return subprocess.check_output(["git", "-C", str(cwd), *args], text=True).strip()

            result.append(
                {
                    "agent": name,
                    "branch": git("branch", "--show-current") or "(detached HEAD)",
                    "head": git("rev-parse", "HEAD"),
                    "tree": git("rev-parse", "HEAD^{tree}"),
                    "latest_commit": git("log", "-1", "--format=%s"),
                    "files_since_start": git("diff", "--name-only", "main...HEAD").splitlines(),
                }
            )
        return result

    def _checkpoints(self):
        previous = (self.version, tuple(b["tree"] for b in self.team_branches()))
        pending = None
        delivered = set()
        while not self.stop_event.is_set():
            self.checkpoint_wake.wait(5)
            self.checkpoint_wake.clear()
            if self.stop_event.is_set():
                return
            try:
                context = (self.version, tuple(b["tree"] for b in self.team_branches()))
                if context != previous:
                    previous, pending, delivered = context, context, set()
                if pending is None:
                    continue
                for name in self.names:
                    if name in delivered:
                        continue
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
                        "Team context changed. Check MidFlight and team branches for "
                        "anything relevant to your task.",
                    )
                    time.sleep(0.5)
                    self.tmux("send-keys", "-t", self.panes[name], "Enter")
                    delivered.add(name)
            except subprocess.CalledProcessError:
                continue

    def report(self):
        result = super().report()
        result["mode"] = "worktree-lab"
        result["repository"] = str(self.theater.repository)
        result["branches"] = self.team_branches()
        result["checks"]["four_claims"] = set(self.names).issubset(
            {c["agent_id"] for c in result["claims"]}
        )
        (self.theater.root / "report.json").write_text(json.dumps(result, indent=2))
        return result


def lab_app(live):
    app = peer_app(live, factory=WorktreeLab)

    @app.get("/team-branches")
    def branches(request: Request):
        current = app.state.live
        actor = current.actor_for(request.headers.get("authorization", ""))
        current.coordination.actor(actor)
        return {
            "branches": current.team_branches(),
            "workflow": "Read committed code with git show; merge needed branches into your own.",
        }

    return app


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8937)
    parser.add_argument("--api-port", type=int, default=8938)
    parser.add_argument("--db-port", type=int, default=6379)
    parser.add_argument("--paused", action="store_true")
    parser.add_argument(
        "--resume-run", type=Path, help="Reattach controller to preserved live worktrees/sessions"
    )
    args = parser.parse_args()
    os.umask(0o077)
    root = Path.home() / ".local/share/midflight-demo" / ("worktrees-" + uuid.uuid4().hex[:10])
    root = args.resume_run.resolve() if args.resume_run else root
    live = WorktreeLab(root, args.db_port, args.api_port, args.port, resume=bool(args.resume_run))
    if not args.paused and not args.resume_run:
        live.launch()
    uvicorn.run(lab_app(live), host="127.0.0.1", port=args.port, access_log=False)


if __name__ == "__main__":
    main()
