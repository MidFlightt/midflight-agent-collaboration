"""Four real local Codex processes, streamed into a browser split screen."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager, suppress
from datetime import UTC, datetime
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse

from midflight.config import Settings
from midflight.main import create_server
from midflight.theater.scenario import change, seed


class Theater:
    def __init__(self, root: Path, db_port: int, api_port: int, *, plan_draft=None, reviewer=None):
        self.repo = Path(__file__).resolve().parents[2]
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=False, mode=0o700)
        self.project = "theater-" + uuid.uuid4().hex[:10]
        self.server = create_server(
            Settings(
                dev_login=True,
                store_backend="falkordb",
                falkor_port=db_port,
                falkor_graph=self.project,
                public_url=f"http://127.0.0.1:{api_port}",
                worker_poll_interval=0.2,
            ),
            reviewer=reviewer,
        )
        self.tokens = seed(self.server.services, self.project, plan_draft)
        self.names = tuple(n for n in self.tokens if n != "lead")
        self.api_port = api_port
        self.db_port = db_port
        self.api = uvicorn.Server(
            uvicorn.Config(self.server.app, host="127.0.0.1", port=api_port, log_level="warning")
        )
        self.lock = threading.RLock()
        self.busy = False
        self.phase = "ready"
        self.stopping = threading.Event()
        self.processes = {}
        self.events = {n: [] for n in self.names}
        self.status = dict.fromkeys(self.names, "ready")
        self.changed = False
        self.baseline_hash = None
        self.commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=self.repo, text=True
        ).strip()
        self.dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=self.repo))
        for name in self.names:
            folder = self.root / name
            folder.mkdir()
            subprocess.run(["git", "init", "-q", "-b", name], cwd=folder, check=True)
            (folder / "TASK.md").write_text(
                f"You own {name}. Implement {name}.py using MidFlight contracts.\n"
                "Use only your workspace. Keep functions small and deterministic.\n"
                "pricing: price()->dict; checkout: checkout(price:dict)->dict; "
                "reporting: report(order:dict)->int; notifications: notify(email:str)->str.\n"
                'Initially use total_cents=1200. Notifications returns "Subscribed: " + email.\n'
            )
            subprocess.run(
                ["git", "-c", "user.name=Demo", "-c", "user.email=demo@localhost", "add", "."],
                cwd=folder,
                check=True,
            )
            subprocess.run(
                [
                    "git",
                    "-c",
                    "user.name=Demo",
                    "-c",
                    "user.email=demo@localhost",
                    "commit",
                    "-qm",
                    "demo task",
                ],
                cwd=folder,
                check=True,
            )
        self.api_thread = threading.Thread(target=self.api.run, daemon=True)
        self.api_thread.start()

    def emit(self, name, message):
        for token in self.tokens.values():
            message = str(message).replace(token, "[redacted]")
        with self.lock:
            self.events[name].append(str(message)[-12000:])
            self.events[name] = self.events[name][-200:]
        with (self.root / f"{name}.log").open("a") as out:
            out.write(str(message) + "\n")

    def agent(self, name, phase):
        config = (
            "mcp_servers.midflight={command="
            + json.dumps(sys.executable)
            + ',args=["-m","midflight.mcp.local.adapter"],env={'
            + ",".join(
                json.dumps(k) + "=" + json.dumps(v)
                for k, v in {
                    "MIDFLIGHT_URL": f"http://127.0.0.1:{self.api_port}",
                    "MIDFLIGHT_TOKEN": self.tokens[name],
                    "MIDFLIGHT_PROJECT": self.project,
                    "PYTHONPATH": str(self.repo),
                }.items()
            )
            + "}}"
        )
        prompt = (
            f"You are the {name} coding agent. Read TASK.md. First use MidFlight MCP check_in "
            f"for task {name}. Submit a complete claim before implementing, including "
            "provided/consumed interfaces with exact fields, files, acceptance criteria, "
            "plan version, branch and base_sha. After approval, implement the task and "
            "run a small local test. Check in once more and explain what you built. "
            "Use only this workspace. Do not commit or change other workspaces. "
            "Finish within this turn. Do not delegate. "
            if phase == "build"
            else f"You are the {name} agent. Read TASK.md and your existing code. "
            f"Use MidFlight MCP check_in for task {name}. Get all new context ONLY from "
            "MidFlight. If a directive affects you, acknowledge it, submit a revised claim "
            "using your existing claim ID and current plan version and exact contracts, "
            "then update and test your code. If no directive affects you, preserve your "
            "existing implementation and explain why. Finish with another check_in. "
            "Do not delegate or access other workspaces."
        )
        command = [
            "codex",
            "exec",
            "--ignore-user-config",
            "--ephemeral",
            "--json",
            "--sandbox",
            "workspace-write",
            "-c",
            'approval_policy="never"',
            "-c",
            config,
            "-C",
            str(self.root / name),
            prompt,
        ]
        for tool in ("check_in", "submit_claim", "acknowledge_directive"):
            command.extend(["-c", f'mcp_servers.midflight.tools.{tool}.approval_mode="approve"'])
        self.status[name] = "working"
        self.emit(name, f"▶ {phase}: real Codex agent starting")
        try:
            proc = subprocess.Popen(
                command,
                cwd=self.root / name,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                start_new_session=True,
            )
            with self.lock:
                self.processes[name] = proc
            timer = threading.Timer(600, lambda: self.terminate(proc))
            timer.start()
            try:
                for line in proc.stdout:
                    try:
                        event = json.loads(line)
                        item = event.get("item", {})
                        message = item.get("text") or item.get("aggregated_output")
                        if not message and item.get("type") == "mcp_tool_call":
                            content = (item.get("result") or {}).get("content", [])
                            reply = "\n".join(c.get("text", "") for c in content)
                            message = (
                                f"MidFlight / {item.get('tool')} / {item.get('status')}\n{reply}"
                            )
                            if item.get("error"):
                                message += "\n" + json.dumps(item["error"])
                        if message:
                            self.emit(name, message)
                        elif event.get("type") in ("error", "turn.failed"):
                            self.emit(name, line.strip())
                    except ValueError:
                        # Keep CLI startup diagnostics separate from the conversation.
                        with (self.root / f"{name}.diagnostics.log").open("a") as diagnostic:
                            diagnostic.write(line)
                proc.wait()
                self.status[name] = "done" if proc.returncode == 0 else "failed"
                self.emit(name, f"■ Agent exited ({proc.returncode})")
            finally:
                timer.cancel()
        except Exception as exc:
            self.status[name] = "failed"
            self.emit(name, f"Agent could not run: {type(exc).__name__}: {exc}")
        finally:
            with self.lock:
                self.processes.pop(name, None)

    @staticmethod
    def terminate(proc):
        if proc.poll() is None:
            with suppress(ProcessLookupError):
                os.killpg(proc.pid, signal.SIGTERM)

    def launch(self, phase):
        with self.lock:
            if self.busy:
                raise HTTPException(409, "Agents are already running")
            if phase == "change" and (self.changed or self.phase != "built"):
                raise HTTPException(409, "Complete the initial build before introducing the change")
            if phase == "build" and self.phase != "ready":
                raise HTTPException(409, "Start a fresh run to repeat the scenario")
            if phase == "change":
                change(self.server.services, self.project)
                self.changed = True
            self.busy = True
            self.phase = phase

        def run():
            try:
                with ThreadPoolExecutor(max_workers=4) as pool:
                    list(pool.map(lambda n: self.agent(n, phase), self.names))
                self.phase = (
                    ("built" if phase == "build" else "changed")
                    if all(s == "done" for s in self.status.values())
                    else "failed"
                )
                report = self.save_report()
                if not all(report["checks"].values()):
                    self.phase = "failed"
                    report["phase"] = "failed"
                    (self.root / "report.json").write_text(json.dumps(report, indent=2))
            finally:
                self.busy = False

        threading.Thread(target=run, daemon=True).start()

    def save_report(self):
        store = self.server.services.store
        claims = store.list_claims(self.project)
        directives = store.list_directives(self.project)
        checks = {
            "four_claims": {c.task_id for c in claims} == set(self.names),
            "all_agents_finished": all(s == "done" for s in self.status.values()),
        }
        if self.changed:
            checks["pricing_and_checkout_notified"] = {"pricing", "checkout"} <= {
                d.task_id for d in directives
            }
            checks["notifications_unaffected"] = not any(
                d.task_id == "notifications" for d in directives
            )
        checks["all_claims_approved"] = bool(claims) and all(
            c.state.value == "approved" for c in claims
        )
        notifications = self.root / "notifications" / "notifications.py"
        if notifications.exists():
            digest = hashlib.sha256(notifications.read_bytes()).hexdigest()
            if not self.changed:
                self.baseline_hash = digest
            elif self.baseline_hash:
                checks["unaffected_code_preserved"] = digest == self.baseline_hash
        integration = self.integration()
        checks["application_integration"] = integration["passed"]
        report = {
            "commit": self.commit,
            "dirty": self.dirty,
            "project": self.project,
            "phase": self.phase,
            "time": datetime.now(UTC).isoformat(),
            "checks": checks,
            "integration": integration,
            "downstream_reporting": "pending dependency-graph integration",
            "agents": self.status,
            "claims": [c.model_dump(mode="json") for c in claims],
            "directives": [d.model_dump(mode="json") for d in directives],
        }
        (self.root / "report.json").write_text(json.dumps(report, indent=2))
        return report

    def integration(self):
        script = """
import importlib.util,sys
from pathlib import Path
root=Path(sys.argv[1]); modules={}
for n in ('pricing','checkout','reporting','notifications'):
    spec=importlib.util.spec_from_file_location(n,root/n/(n+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);modules[n]=module
price=modules['pricing'].price(); assert price['total_cents']==1200
if sys.argv[2]=='changed': assert isinstance(price['currency'],str) and price['currency']
if sys.argv[2]=='subscription': assert price['billing_interval']=='monthly'
order=modules['checkout'].checkout(price); assert order['total_cents']==1200
if sys.argv[2]=='subscription':
    assert order['billing_interval']=='monthly'
    assert isinstance(order['subscription_id'],str) and order['subscription_id']
assert modules['reporting'].report(order)==1200
assert modules['notifications'].notify('demo@example.com')=='Subscribed: demo@example.com'
print('Commerce integration passed')
"""
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-I",
                    "-c",
                    script,
                    str(self.root),
                    "subscription"
                    if getattr(self, "subscription", False)
                    else "changed"
                    if self.changed
                    else "initial",
                ],
                capture_output=True,
                text=True,
                timeout=15,
            )
            return {
                "passed": result.returncode == 0,
                "output": (result.stdout + result.stderr)[-4000:],
            }
        except subprocess.TimeoutExpired:
            return {"passed": False, "output": "Integration timed out"}

    def snapshot(self):
        with self.lock:
            return {
                "phase": self.phase,
                "busy": self.busy,
                "commit": self.commit[:10],
                "dirty": self.dirty,
                "agents": {
                    n: {"status": self.status[n], "events": list(self.events[n])}
                    for n in self.names
                },
            }

    def close(self):
        self.stopping.set()
        with self.lock:
            for proc in self.processes.values():
                self.terminate(proc)
        self.api.should_exit = True
        self.api_thread.join(35)


def dashboard(theater):
    @asynccontextmanager
    async def lifespan(app):
        yield
        theater.close()

    app = FastAPI(lifespan=lifespan)

    @app.middleware("http")
    async def local_only(request: Request, call_next):
        if request.method == "POST":
            origin = request.headers.get("origin")
            if origin and origin != str(request.base_url).rstrip("/"):
                from starlette.responses import JSONResponse

                return JSONResponse({"detail": "Local dashboard requests only"}, status_code=403)
        return await call_next(request)

    @app.get("/")
    def index():
        return HTMLResponse(Path(__file__).with_name("index.html").read_text())

    @app.get("/state")
    def state():
        return theater.snapshot()

    @app.post("/run/{phase}")
    def run(phase: str):
        if phase not in ("build", "change"):
            raise HTTPException(404)
        theater.launch(phase)
        return {"started": phase}

    @app.post("/new")
    def new_run():
        nonlocal theater
        if theater.busy:
            raise HTTPException(409, "Wait for the current agents to finish")
        root, db_port, api_port = theater.root.parent, theater.db_port, theater.api_port
        theater.close()
        theater = Theater(root / uuid.uuid4().hex[:12], db_port, api_port)
        return {"ready": True}

    @app.get("/report")
    def report():
        return theater.save_report()

    return app


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--api-port", type=int, default=8766)
    parser.add_argument("--db-port", type=int, default=6379)
    parser.add_argument("--runs", type=Path, default=Path.home() / ".local/share/midflight-demo")
    args = parser.parse_args()
    if not shutil.which("codex"):
        parser.error("Install and sign in to Codex CLI first")
    for port in (args.port, args.api_port):
        try:
            with socket.socket() as listener:
                listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                listener.bind(("127.0.0.1", port))
        except OSError:
            parser.error(f"Local port {port} is busy; choose --port and --api-port")
    theater = Theater(args.runs / uuid.uuid4().hex[:12], args.db_port, args.api_port)
    print(f"Four-agent demo: http://127.0.0.1:{args.port} — artifacts: {theater.root}", flush=True)
    uvicorn.run(dashboard(theater), host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
