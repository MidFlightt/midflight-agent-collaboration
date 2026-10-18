"""Restart a peer controller against its existing graph, credentials and tmux session."""

import argparse
import hashlib
import json
import secrets
import subprocess
import threading
import tomllib
from pathlib import Path

import uvicorn

from midflight.config import Settings
from midflight.main import create_server
from midflight.theater.app import Theater
from midflight.theater.delivery_fixture import DeliveryTheater
from midflight.theater.peer_coordination import PeerCoordination
from midflight.theater.peers import peer_app
from midflight.theater.reviewed_assumptions import install_reviewed_assumptions


def restore(root, *, db_port=6379, api_port=8910, port=8909):
    """Read a saved delivery session; never seed a graph or launch/overwrite agents."""
    root = Path(root).resolve()
    metadata = json.loads((root / "interactive.json").read_text())
    report = json.loads((root / "report.json").read_text())
    live = DeliveryTheater.__new__(DeliveryTheater)
    live.session, live.panes = metadata["session"], metadata["panes"]
    live.names = tuple(live.panes)
    live.tmux("has-session", "-t", live.session)
    tokens = {}
    for name in live.names:
        command = json.loads((root / f"{name}-launch.json").read_text())
        config = next(c for c in command if c.startswith("mcp_servers.theater_midflight="))
        env = tomllib.loads(config)["mcp_servers"]["theater_midflight"]["env"]
        if (
            env["MIDFLIGHT_PROJECT"] != metadata["project"]
            or env["MIDFLIGHT_URL"] != f"http://127.0.0.1:{api_port}"
            or env["MIDFLIGHT_DEMO_CONTROLLER"] != f"http://127.0.0.1:{port}"
        ):
            raise ValueError("Resume ports/project do not match the existing agents")
        tokens[name] = env["MIDFLIGHT_TOKEN"]
    theater = live.theater = Theater.__new__(Theater)
    theater.root, theater.repo = root, Path(__file__).resolve().parents[2]
    theater.project, theater.tokens, theater.names = metadata["project"], tokens, live.names
    theater.api_port, theater.db_port = api_port, db_port
    theater.server = create_server(
        Settings(
            dev_login=True,
            store_backend="falkordb",
            falkor_port=db_port,
            falkor_graph=theater.project,
            public_url=f"http://127.0.0.1:{api_port}",
            worker_poll_interval=0.2,
            worker_concurrency=2,
        ),
        reviewer=live.reviewer(),
    )
    store = theater.server.services.store
    project = store.get_project(theater.project)
    if project is None or project.current_plan_version is None:
        raise ValueError("Saved graph has no current plan")
    for name, token in tokens.items():
        member = store.get_participant(name)
        if (
            member is None
            or member.project_id != theater.project
            or not secrets.compare_digest(
                member.token_hash or "", hashlib.sha256(token.encode()).hexdigest()
            )
        ):
            raise ValueError("Saved agent identity is no longer valid")
    install_reviewed_assumptions(theater.server)
    live.coordination = PeerCoordination(theater.server.services, theater.project)
    theater.api = uvicorn.Server(
        uvicorn.Config(theater.server.app, host="127.0.0.1", port=api_port, log_level="warning")
    )
    theater.api_thread = threading.Thread(target=theater.api.run, daemon=True)
    theater.lock, theater.stopping = threading.RLock(), threading.Event()
    theater.processes, theater.busy, theater.phase = {}, False, "resumed"
    theater.events = {n: [] for n in live.names}
    theater.status = dict.fromkeys(live.names, "resumed")
    theater.changed, theater.baseline_hash = bool(report.get("direction")), None
    theater.commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=theater.repo, text=True
    ).strip()
    theater.dirty = bool(
        subprocess.check_output(["git", "status", "--porcelain"], cwd=theater.repo)
    )
    live.controller_port, live.key = port, secrets.token_urlsafe(24)
    live.changed, live.direction = theater.changed, report.get("direction")
    live.version = project.current_plan_version
    live.events = report.get("visual_events", [])
    live.cues, live.check_ins = dict.fromkeys(live.names, "unchanged"), dict.fromkeys(live.names, 0)
    for event in live.events:
        if event["type"] == "check_in" and event.get("agent") in live.names:
            live.check_ins[event["agent"]] += 1
    live.guard, live.stop_event = threading.RLock(), threading.Event()
    live.checkpoint_wake, live.poller, live.checkpoint_counts = threading.Event(), None, {}
    return live


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--port", type=int, default=8909)
    parser.add_argument("--api-port", type=int, default=8910)
    args = parser.parse_args()
    live = restore(args.root, api_port=args.api_port, port=args.port)
    live.theater.api_thread.start()
    uvicorn.run(peer_app(live), host="127.0.0.1", port=args.port, access_log=False)


if __name__ == "__main__":
    main()
