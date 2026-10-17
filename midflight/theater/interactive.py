"""Real persistent Codex terminals; tmux owns sessions while the browser attaches."""

from __future__ import annotations

import argparse
import asyncio
import fcntl
import json
import os
import pty
import secrets
import shlex
import shutil
import signal
import socket
import struct
import subprocess
import sys
import termios
import time
import uuid
from contextlib import asynccontextmanager, suppress
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from midflight.theater.app import Theater
from midflight.theater.scenario import NAMES, change


class InteractiveTheater:
    def __init__(self, root: Path, db_port: int, api_port: int):
        self.theater = Theater(root, db_port, api_port)
        self.session = "midflight-" + uuid.uuid4().hex[:8]
        self.key = secrets.token_urlsafe(24)
        self.panes = {}
        self.changed = False

    def tmux(self, *args):
        return subprocess.check_output(["tmux", *args], text=True).strip()

    def launch(self):
        theater = self.theater
        for i, name in enumerate(NAMES):
            config = (
                "mcp_servers.theater_midflight={command="
                + json.dumps(sys.executable)
                + ',args=["-m","midflight.mcp.local.adapter"],env={'
                + ",".join(
                    json.dumps(k) + "=" + json.dumps(v)
                    for k, v in {
                        "MIDFLIGHT_URL": f"http://127.0.0.1:{theater.api_port}",
                        "MIDFLIGHT_TOKEN": theater.tokens[name],
                        "MIDFLIGHT_PROJECT": theater.project,
                        "PYTHONPATH": str(theater.repo),
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
            for tool in ("check_in", "submit_claim", "acknowledge_directive"):
                command += [
                    "-c",
                    f'mcp_servers.theater_midflight.tools.{tool}.approval_mode="approve"',
                ]
            command.append(prompt)
            launch = theater.root / (name + "-launch.json")
            launch.write_text(json.dumps(command))
            launch.chmod(0o600)
            launcher = theater.root / (name + "-launch.py")
            codex_profile_dir = theater.root / (name + "-codex-profile")
            codex_profile_dir.mkdir(mode=0o700)
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
        self.tmux("swap-pane", "-s", self.panes["checkout"], "-t", self.panes["notifications"])
        self.tmux("select-pane", "-t", self.panes["pricing"])
        metadata = {
            "session": self.session,
            "panes": self.panes,
            "root": str(theater.root),
            "commit": theater.commit,
            "project": theater.project,
        }
        (theater.root / "interactive.json").write_text(json.dumps(metadata, indent=2))

    def introduce_change(self):
        if self.changed:
            raise HTTPException(409, "Change already introduced")
        report = self.theater.save_report()
        if not (
            report["checks"]["four_claims"]
            and report["checks"]["all_claims_approved"]
            and report["checks"]["application_integration"]
        ):
            raise HTTPException(
                409, "Wait for all four approved claims and the integrated initial build"
            )
        change(self.theater.server.services, self.theater.project)
        self.changed = self.theater.changed = True
        for pane in self.panes.values():
            self.tmux(
                "send-keys",
                "-t",
                pane,
                "-l",
                "Checkpoint: use MidFlight check_in now. Obtain new context only from MidFlight. "
                "Handle relevant directives, acknowledge them and revise your "
                "existing claim before "
                "changing code. If unaffected preserve your code. Test, check in and summarize.",
            )
            # Codex groups fast terminal input as pasted text. Wait for that
            # buffer to settle so Enter submits rather than inserting a newline.
            time.sleep(0.5)
            self.tmux("send-keys", "-t", pane, "Enter")

    def report(self):
        report = self.theater.save_report()
        # Interactive processes remain alive at the prompt; completion is established
        # by saved claims and independent tests, never by process exit status.
        report["checks"].pop("all_agents_finished", None)
        report["mode"] = "persistent-interactive"
        report["phase"] = "changed" if self.changed else "initial"
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
        with suppress(subprocess.CalledProcessError):
            self.tmux("kill-session", "-t", self.session)
        self.theater.close()


def terminal_app(live):
    @asynccontextmanager
    async def lifespan(app):
        yield
        live.close()

    app = FastAPI(lifespan=lifespan)
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

    @app.post("/change")
    def plan_change(request: Request):
        if request.headers.get("x-demo-key") != live.key:
            raise HTTPException(403)
        live.introduce_change()
        return {"changed": True}

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

        proc = subprocess.Popen(
            ["tmux", "attach-session", "-t", live.session],
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
    live = InteractiveTheater(root, args.db_port, args.api_port)
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
