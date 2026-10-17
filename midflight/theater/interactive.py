"""Real persistent Codex terminals; tmux owns sessions while the browser attaches."""

from __future__ import annotations

import argparse
import asyncio
import fcntl
import json
import os
import pty
import re
import secrets
import shlex
import shutil
import signal
import socket
import struct
import subprocess
import sys
import termios
import threading
import time
import uuid
from contextlib import asynccontextmanager, suppress
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from midflight.domain.models import Role
from midflight.ports import Commit
from midflight.theater.app import Theater
from midflight.theater.scenario import NAMES, subscription_direction


class InteractiveTheater:
    names = NAMES
    submit_initial_prompt = True

    mcp_module = "midflight.theater.agent_mcp"

    def initial_prompt(self, name, default):
        return default

    def plan_tools(self, name):
        return ["set_direction"] if name == "pricing" else []

    def reviewer(self):
        return None

    def initial_plan(self):
        return None

    def __init__(self, root: Path, db_port: int, api_port: int, controller_port: int = 8897):
        self.theater = Theater(
            root, db_port, api_port, plan_draft=self.initial_plan(), reviewer=self.reviewer()
        )
        self.names = self.theater.names
        self.session = "midflight-" + uuid.uuid4().hex[:8]
        self.key = secrets.token_urlsafe(24)
        self.panes = {}
        self.changed = False
        self.controller_port = controller_port
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
        store = self.theater.server.services.store
        pricing = store.get_participant(self.names[0]).model_copy(update={"role": Role.LEAD})
        project = store.get_project(self.theater.project).model_copy(
            update={"lead_id": self.names[0]}
        )
        store.commit(Commit(self.theater.project, "demo-pricing-lead", puts=[pricing, project]))
        specifications = {
            "pricing": 'price() -> dict, initially {"total_cents": 1200}. '
            "You also serve as team lead.",
            "checkout": "checkout(price: dict) -> dict. Initially copy total_cents into an order.",
            "reporting": 'report(order: dict) -> int. Initially return order["total_cents"].',
            "notifications": 'notify(email: str) -> str. Return exactly "Subscribed: " + email.',
        }
        for name, spec in specifications.items():
            if name not in self.names:
                continue
            (self.theater.root / name / "TASK.md").write_text(
                f"You own {name}. Implement {name}.py. {spec}\n"
                "Obtain shared contracts only through MidFlight. Use only this workspace.\n"
                "Check in before each implementation step and after testing. Handle relevant "
                "directives with acknowledgement and a revised claim before changing code.\n"
                "Avoid assumptions about unrelated tasks; "
                "do not name unrelated tasks in assumptions.\n"
            )

    def tmux(self, *args):
        return subprocess.check_output(["tmux", *args], text=True).strip()

    def launch(self):
        theater = self.theater
        for i, name in enumerate(self.names):
            config = (
                "mcp_servers.theater_midflight={command="
                + json.dumps(sys.executable)
                + ',args=["-m",'
                + json.dumps(self.mcp_module)
                + "],env={"
                + ",".join(
                    json.dumps(k) + "=" + json.dumps(v)
                    for k, v in {
                        "MIDFLIGHT_URL": f"http://127.0.0.1:{theater.api_port}",
                        "MIDFLIGHT_TOKEN": theater.tokens[name],
                        "MIDFLIGHT_PROJECT": theater.project,
                        "PYTHONPATH": str(theater.repo),
                        "MIDFLIGHT_DEMO_CONTROLLER": f"http://127.0.0.1:{self.controller_port}",
                        "MIDFLIGHT_DEMO_AGENT": name,
                    }.items()
                )
                + "}}"
            )
            prompt = (
                f"You are the {name} agent. Read TASK.md. Use ONLY the local theater_midflight MCP "
                f"server to check_in for task {name}. Submit a complete claim with the exact plan "
                "contracts, correct no_interfaces setting when none, "
                "files and acceptance criteria. "
                "After approval implement the function in TASK.md and test it. "
                "Finish with check_in "
                "and a short summary. Do not commit, push, delegate or access other workspaces. "
                "Stay in this same session for later stages; finish this turn when done."
            )
            if name == "pricing":
                prompt += (
                    " You are also the team lead. The HUMAN will type product directions here. "
                    "When they do, FIRST call set_direction with their exact words; then check in "
                    "for your own pricing task and handle its directive. Do not invent a direction "
                    "during this initial build. "
                    "Do not distribute the change to other agents yourself."
                )
            else:
                prompt += (
                    " At each checkpoint, use check_in and handle relevant directives before "
                    "continuing. Periodic neutral checkpoint requests may arrive while you work."
                )
            prompt = self.initial_prompt(name, prompt)
            command = [
                "codex",
                "--no-daemon",
                "-s",
                "workspace-write",
                "-a",
                "never",
                "-c",
                config,
                "-c",
                f'projects.{json.dumps(str(theater.root / name))}.trust_level="trusted"',
                "-C",
                str(theater.root / name),
            ]
            tools = ["check_in", "submit_claim", "acknowledge_directive"]
            tools.extend(self.plan_tools(name))
            for tool in tools:
                command += [
                    "-c",
                    f'mcp_servers.theater_midflight.tools.{tool}.approval_mode="approve"',
                ]
            if self.submit_initial_prompt:
                command.append(prompt)
            launch = theater.root / (name + "-launch.json")
            launch.write_text(json.dumps(command))
            launch.chmod(0o600)
            launcher = theater.root / (name + "-launch.py")
            codex_profile_dir = theater.root / (name + "-codex-profile")
            codex_profile_dir.mkdir(mode=0o700)
            (codex_profile_dir / "config.toml").write_text(
                f"[projects.{json.dumps(str((theater.root / name).resolve()))}]\n"
                'trust_level="trusted"\n'
            )
            auth_file = Path.home() / ".codex" / "auth.json"
            if not auth_file.exists():
                raise RuntimeError("Sign in using codex login before launching the demo")
            (codex_profile_dir / "auth.json").symlink_to(auth_file)
            launcher.write_text(
                "import json,os\nfrom pathlib import Path\n"
                'args=json.loads(Path(__file__).with_suffix(".json").read_text())\n'
                + "os.environ['CODEX_HOME']="
                + repr(str(codex_profile_dir))
                + "\n"
                + "os.execvp(args[0],args)\n"
            )
            shell_command = shlex.join([sys.executable, str(launcher)])
            if i == 0:
                pane = self.tmux(
                    "new-session",
                    "-d",
                    "-P",
                    "-F",
                    "#{pane_id}",
                    "-s",
                    self.session,
                    "-x",
                    "220",
                    "-y",
                    "62",
                    shell_command,
                )
                self.tmux("set-option", "-t", self.session, "remain-on-exit", "on")
                self.tmux("set-option", "-t", self.session, "mouse", "on")
                self.tmux("set-option", "-t", self.session, "pane-border-status", "top")
                self.tmux("set-option", "-t", self.session, "pane-border-format", " #{pane_title} ")
                self.tmux("set-option", "-t", self.session, "status-left", " MidFlight | ")
                self.tmux(
                    "set-option",
                    "-t",
                    self.session,
                    "status-right",
                    "Ctrl-b arrows: switch | Ctrl-b z: zoom",
                )
            else:
                pane = self.tmux(
                    "split-window",
                    "-d",
                    "-P",
                    "-F",
                    "#{pane_id}",
                    "-t",
                    self.session,
                    shell_command,
                )
            self.panes[name] = pane
            self.tmux("select-pane", "-t", pane, "-T", name.title())
            self.tmux("select-layout", "-t", self.session, "tiled")
        self.tmux("swap-pane", "-s", self.panes[self.names[1]], "-t", self.panes[self.names[3]])
        self.tmux("select-pane", "-t", self.panes[self.names[0]])
        self.tmux(
            "select-pane",
            "-t",
            self.panes[self.names[0]],
            "-T",
            "PRICING / LEAD — type direction here",
        )
        self.poller = threading.Thread(target=self._checkpoints, daemon=True)
        self.poller.start()
        metadata = {
            "session": self.session,
            "panes": self.panes,
            "root": str(theater.root),
            "commit": theater.commit,
            "project": theater.project,
        }
        (theater.root / "interactive.json").write_text(json.dumps(metadata, indent=2))

    def actor_for(self, authorization):
        token = authorization.removeprefix("Bearer ")
        for name, saved in self.theater.tokens.items():
            if secrets.compare_digest(token, saved):
                return name
        raise HTTPException(401, "Invalid demo identity")

    def set_direction(self, name, direction):
        if name != "pricing":
            raise HTTPException(403, "Only the lead can change direction")
        if not isinstance(direction, str) or not 1 <= len(direction) <= 1000:
            raise HTTPException(422, "Supply the human direction as text")
        with self.guard:
            if self.changed:
                if direction == self.direction:
                    return {"plan_version": self.version, "direction": self.direction}
                raise HTTPException(409, "Reset the demo before another product pivot")
            # Preserve a baseline if the independent implementation already exists.
            self.theater.save_report()
            services = self.theater.server.services
            actor = services.store.get_participant(name)
            if actor.role is not Role.LEAD or not actor.active:
                raise HTTPException(403, "The lead membership is not active")
            try:
                plan = subscription_direction(services, self.theater.project, actor, direction)
            except ValueError as error:
                raise HTTPException(422, str(error)) from error
            self.changed = self.theater.changed = self.theater.subscription = True
            self.direction, self.version = direction, plan.version
            self.cues.update(pricing="direction", checkout="waiting", reporting="waiting")
            self.record(
                "direction_accepted", "pricing", direction=direction, plan_version=plan.version
            )
            self.checkpoint_wake.set()
            return {
                "plan_version": self.version,
                "direction": self.direction,
                "note": "Other agents learn this at their own MidFlight check-ins.",
            }

    def record(self, kind, name, **details):
        from datetime import UTC, datetime

        event = {"type": kind, "agent": name, "time": datetime.now(UTC).isoformat(), **details}
        self.events.append(event)
        with (self.theater.root / "events.jsonl").open("a") as out:
            out.write(json.dumps(event) + "\n")

    def observed(self, name):
        if name not in self.names:
            raise HTTPException(403, "Not a demo task")
        with self.guard:
            self.check_ins[name] += 1
            directives = [
                d
                for d in self.theater.server.services.store.list_directives(
                    self.theater.project, name
                )
                if d.plan_version == self.version
            ]
            if self.changed and directives:
                self.cues[name] = (
                    "acknowledged"
                    if all(d.state.value == "acknowledged" for d in directives)
                    else "received"
                )
            self.record("check_in", name, cue=self.cues[name], count=self.check_ins[name])
            return {"observed": True}

    def status(self):
        with self.guard:
            return {
                "session": self.session,
                "direction": self.direction,
                "version": self.version,
                "cues": dict(self.cues),
                "check_ins": dict(self.check_ins),
                "events": list(self.events[-30:]),
                "layout": self.layout(),
            }

    def layout(self):
        names = {pane: name for name, pane in self.panes.items()}
        output = self.tmux(
            "list-panes",
            "-t",
            self.session,
            "-F",
            "#{pane_id} #{pane_left} #{pane_top} #{pane_width} #{pane_height}",
        )
        return {
            names[parts[0]]: dict(
                zip(("x", "y", "width", "height"), map(int, parts[1:]), strict=True)
            )
            for line in output.splitlines()
            if (parts := line.split()) and parts[0] in names
        }

    def _checkpoints(self):
        while not self.stop_event.is_set():
            self.checkpoint_wake.wait(15)
            self.checkpoint_wake.clear()
            if self.stop_event.is_set():
                return
            for name in ("checkout", "reporting", "notifications"):
                if self.stop_event.is_set():
                    return
                counter = (self.version, name)
                if self.checkpoint_counts.get(counter, 0) >= 6:
                    continue  # Bound model usage while waiting for a human direction.
                if self.changed and self.cues[name] == "acknowledged":
                    continue
                if self.changed and name == "notifications" and self.checkpoint_counts.get(counter):
                    continue
                try:
                    screen = self.tmux("capture-pane", "-p", "-t", self.panes[name])
                    tail = "\n".join(screen.splitlines()[-14:])
                    if "Ask Codex to do anything" not in tail or re.search(
                        r"esc to interrupt|Starting MCP|Working \(", tail, re.IGNORECASE
                    ):
                        continue
                    self.tmux(
                        "send-keys",
                        "-t",
                        self.panes[name],
                        "-l",
                        "Scheduled checkpoint: call theater_midflight.check_in for your task. "
                        "Handle any relevant directives: acknowledge, revise your existing claim, "
                        "then update/test if needed. If unaffected preserve your work. "
                        "Do not infer or invent a change; use MidFlight context only.",
                    )
                    time.sleep(0.5)
                    self.tmux("send-keys", "-t", self.panes[name], "Enter")
                    self.checkpoint_counts[counter] = self.checkpoint_counts.get(counter, 0) + 1
                except subprocess.CalledProcessError:
                    continue

    def report(self):
        report = self.theater.save_report()
        # Interactive processes remain alive at the prompt; completion is established
        # by saved claims and independent tests, never by process exit status.
        report["checks"].pop("all_agents_finished", None)
        report["mode"] = "persistent-interactive"
        report["phase"] = "changed" if self.changed else "initial"
        report["human_direction"] = self.direction
        report["visual_events"] = list(self.events)
        if self.changed:
            directives = self.theater.server.services.store.list_directives(self.theater.project)
            report["checks"]["subscription_tasks_notified"] = {
                "pricing",
                "checkout",
                "reporting",
            } <= {d.task_id for d in directives}
        report["agents"] = {
            name: {
                "pane": pane,
                "pid": self.tmux("display-message", "-p", "-t", pane, "#{pane_pid}"),
                "alive": self.tmux("display-message", "-p", "-t", pane, "#{pane_dead}") == "0",
            }
            for name, pane in self.panes.items()
        }
        report["checks"]["sessions_alive"] = all(a["alive"] for a in report["agents"].values())
        report["session"] = self.session
        report["panes"] = self.panes
        (self.theater.root / "report.json").write_text(json.dumps(report, indent=2))
        return report

    def close(self):
        self.stop_event.set()
        self.checkpoint_wake.set()
        if self.poller is not None and self.poller is not threading.current_thread():
            self.poller.join(5)
        with suppress(subprocess.CalledProcessError):
            self.tmux("kill-session", "-t", self.session)
        self.theater.close()


def terminal_app(live, *, factory=None, allow_staged_reset=False):
    @asynccontextmanager
    async def lifespan(app):
        yield
        live.close()

    control_lock = threading.RLock()
    app = FastAPI(lifespan=lifespan)
    app.state.live = live
    app.state.control_lock = control_lock
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])
    app.mount("/vendor", StaticFiles(directory=Path(__file__).with_name("vendor")), name="vendor")

    @app.get("/")
    def index():
        return FileResponse(Path(__file__).with_name("terminal.html"))

    @app.get("/connection")
    def connection(request: Request):
        if request.headers.get("sec-fetch-site") == "cross-site":
            raise HTTPException(403)
        return {"key": live.key, "commit": live.theater.commit[:10], "session": live.session}

    @app.get("/status")
    def status(request: Request):
        if request.headers.get("x-demo-key") != live.key:
            raise HTTPException(403)
        return live.status()

    @app.post("/direction")
    def direction(request: Request, body: dict):
        with control_lock:
            name = live.actor_for(request.headers.get("authorization", ""))
            return live.set_direction(name, body.get("direction"))

    @app.post("/observed")
    def observed(request: Request):
        with control_lock:
            name = live.actor_for(request.headers.get("authorization", ""))
            return live.observed(name)

    @app.post("/reset")
    def reset(request: Request):
        nonlocal live
        with control_lock:
            if request.headers.get("x-demo-key") != live.key:
                raise HTTPException(403)
            old = live
            old.report()
            old.close()
            root = old.theater.root.parent / ("interactive-" + uuid.uuid4().hex[:10])
            live = (factory or InteractiveTheater)(
                root, old.theater.db_port, old.theater.api_port, old.controller_port
            )
            if not allow_staged_reset or request.query_params.get("start") != "false":
                live.launch()
            app.state.live = live
            return {"reset": True, "session": live.session}

    @app.get("/report")
    def report():
        return live.report()

    @app.websocket("/terminal")
    async def terminal(ws: WebSocket):
        origin = ws.headers.get("origin")
        expected = "http://" + ws.headers.get("host", "")
        if origin != expected or ws.query_params.get("key") != live.key:
            await ws.close(code=1008)
            return
        await ws.accept()
        master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 62, 220, 0, 0))

        def setup_terminal():
            os.setsid()
            fcntl.ioctl(0, termios.TIOCSCTTY, 0)

        attached_session = live.session
        proc = subprocess.Popen(
            ["tmux", "attach-session", "-t", attached_session],
            stdin=slave,
            stdout=slave,
            stderr=slave,
            preexec_fn=setup_terminal,
            env={**os.environ, "TERM": "xterm-256color"},
        )
        os.close(slave)

        async def output():
            while True:
                data = await asyncio.to_thread(os.read, master, 65536)
                if not data:
                    return
                await ws.send_bytes(data)

        async def input_():
            while True:
                message = json.loads(await ws.receive_text())
                if message.get("type") == "resize":
                    cols = max(40, min(500, int(message["cols"])))
                    rows = max(12, min(200, int(message["rows"])))
                    fcntl.ioctl(master, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))
                    os.kill(proc.pid, signal.SIGWINCH)
                    # The first resize can beat tmux's SIGWINCH handler during attach.
                    # Size the existing window explicitly and rebalance the four panes.
                    with suppress(subprocess.CalledProcessError):
                        await asyncio.to_thread(
                            live.tmux,
                            "resize-window",
                            "-t",
                            attached_session,
                            "-x",
                            str(cols),
                            "-y",
                            str(rows),
                        )
                        await asyncio.to_thread(
                            live.tmux, "select-layout", "-t", attached_session, "tiled"
                        )
                elif message.get("type") == "input":
                    os.write(master, message["data"].encode())

        tasks = [asyncio.create_task(output()), asyncio.create_task(input_())]
        try:
            await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        except (WebSocketDisconnect, OSError):
            pass
        finally:
            proc.terminate()
            await asyncio.to_thread(proc.wait)
            os.close(master)
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    return app


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8897)
    parser.add_argument("--api-port", type=int, default=8898)
    parser.add_argument("--db-port", type=int, default=6379)
    args = parser.parse_args()
    if not shutil.which("tmux") or not shutil.which("codex"):
        parser.error("Install tmux and sign in to Codex before starting")
    if args.port == args.api_port:
        parser.error("Terminal and API ports must differ")
    for port in (args.port, args.api_port):
        try:
            with socket.socket() as listener:
                listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                listener.bind(("127.0.0.1", port))
        except OSError:
            parser.error(f"Port {port} is busy; choose another port before launching agents")
    os.umask(0o077)
    root = Path.home() / ".local/share/midflight-demo" / ("interactive-" + uuid.uuid4().hex[:10])
    live = InteractiveTheater(root, args.db_port, args.api_port, args.port)
    try:
        live.launch()
        print(
            f"Interactive coding terminals: http://127.0.0.1:{args.port} | {live.session}",
            flush=True,
        )
        uvicorn.run(terminal_app(live), host="127.0.0.1", port=args.port, access_log=False)
    finally:
        live.close()


if __name__ == "__main__":
    main()
