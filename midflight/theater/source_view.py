"""Read-only observer: real workspace files plus the running demo's coordination data."""

import argparse
import hashlib
import json
import os
import secrets
import threading
import time
from collections import deque
from pathlib import Path
from urllib.parse import urlparse

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

SUFFIXES = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".json",
    ".html",
    ".css",
    ".md",
    ".toml",
    ".yaml",
    ".yml",
    ".txt",
    ".sql",
    ".rs",
    ".go",
    ".java",
    ".sh",
}
SKIP = {"node_modules", "__pycache__", "venv", "dist", "build"}


class WorkspaceObserver:
    def __init__(self):
        self.project = None
        self.previous = {}
        self.events = deque(maxlen=80)
        self.counter = 0
        self.baseline = False
        self.workspaces = set()

    def scan(self, root: Path, project: str, names: list[str]):
        if self.project != project:
            self.project, self.previous = project, {}
            self.events.clear()
            self.baseline = False
            self.workspaces.clear()
        current = {}
        errors = []
        incomplete = set()
        for name in names:
            # Participant names may not select paths outside this run.
            if Path(name).name != name or name in {".", ".."}:
                continue
            workspace = root / name
            if not workspace.is_dir() or workspace.is_symlink():
                continue
            count = 0
            for folder, dirs, files in os.walk(
                workspace,
                followlinks=False,
                onerror=lambda error, workspace_name=name: (
                    errors.append(f"Could not list {workspace_name}"),
                    incomplete.add(workspace_name),
                ),
            ):
                dirs[:] = sorted(
                    d
                    for d in dirs
                    if not d.startswith(".")
                    and d not in SKIP
                    and not (Path(folder) / d).is_symlink()
                )
                for name_on_disk in sorted(files):
                    path = Path(folder) / name_on_disk
                    if (
                        path.is_symlink()
                        or name_on_disk.startswith(".")
                        or name_on_disk == "TASK.md"
                    ):
                        continue
                    if path.suffix.lower() not in SUFFIXES:
                        continue
                    if count >= 300:
                        errors.append(f"File limit reached in {name}")
                        incomplete.add(name)
                        dirs[:] = []
                        break
                    try:
                        stat = path.stat()
                        if stat.st_size > 2_000_000:
                            incomplete.add(name)
                            errors.append(
                                f"Oversized file excluded: {name}/{path.relative_to(workspace)}"
                            )
                            continue
                        digest = hashlib.sha256(path.read_bytes()).hexdigest()
                    except OSError:
                        incomplete.add(name)
                        errors.append(f"Could not read: {name}/{path.relative_to(workspace)}")
                        continue
                    relative = path.relative_to(workspace).as_posix()
                    key = f"disk:{name}:{relative}"
                    previous = self.previous.get(key)
                    current[key] = {
                        "id": key,
                        "kind": "file",
                        "label": relative,
                        "agent_id": f"agent:{name}",
                        "origin": "filesystem",
                        "size": stat.st_size,
                        "sha256": digest,
                        "mtime_ns": stat.st_mtime_ns,
                        "observation": "present",
                        "event_id": previous.get("event_id", 0) if previous else 0,
                    }
                    change = (
                        "created"
                        if previous is None
                        else ("modified" if previous["sha256"] != digest else None)
                    )
                    if self.baseline and name in self.workspaces and change:
                        self.counter += 1
                        current[key]["event_id"] = self.counter
                        current[key]["observation"] = change
                        self.events.append(
                            {
                                "id": self.counter,
                                "type": change,
                                "agent": name,
                                "path": relative,
                                "time": time.time(),
                            }
                        )
                    count += 1
        if self.baseline:
            for key, previous in self.previous.items():
                if key not in current:
                    if previous["agent_id"].removeprefix("agent:") in incomplete:
                        current[key] = {**previous, "observation": "unavailable"}
                        continue
                    self.counter += 1
                    self.events.append(
                        {
                            "id": self.counter,
                            "type": "removed",
                            "agent": previous["agent_id"].removeprefix("agent:"),
                            "path": previous["label"],
                            "time": time.time(),
                        }
                    )
        self.workspaces.update(names)
        self.previous, self.baseline = current, True
        return list(current.values()), list(self.events), errors


class SourceView:
    def __init__(self, upstream: str, runs: Path):
        parsed = urlparse(upstream)
        if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"}:
            raise ValueError("The observer only attaches to a local demo")
        self.upstream = upstream.rstrip("/")
        self.client = httpx.Client(base_url=self.upstream, timeout=15)
        self.runs = runs
        self.root = None
        self.project = None
        self.observer = WorkspaceObserver()
        self.lock = threading.RLock()
        self.key = secrets.token_urlsafe(24)

    def snapshot(self):
        with self.lock:
            # Read only: these requests do not alter the plan, agent input or sessions.
            key = self.client.get("/connection").raise_for_status().json()["key"]
            raw = (
                self.client.get("/graph-state", headers={"x-demo-key": key})
                .raise_for_status()
                .json()
            )
            report = self.client.get("/report").raise_for_status().json()
            if raw["project"] != report["project"]:
                raise RuntimeError("Run changed while reading; retrying next poll")
            if self.project != raw["project"] or self.root is None:
                self.root, self.project = None, raw["project"]
                for path in sorted(
                    self.runs.glob("*/report.json"), key=lambda p: p.stat().st_mtime, reverse=True
                ):
                    try:
                        if json.loads(path.read_text()).get("project") == self.project:
                            self.root = path.parent
                            break
                    except (OSError, ValueError):
                        continue
            if self.root is None:
                raise RuntimeError("Workspace for this run could not be located")
            names = [n["label"] for n in raw["nodes"] if n["kind"] == "agent"]
            files, events, errors = self.observer.scan(self.root, self.project, names)
            return {
                **raw,
                "workspace_files": files,
                "file_events": events,
                "observer_errors": errors,
                "coding_url": self.upstream,
                "source": "FalkorDB claims + local filesystem observation",
            }


def create_app(view):
    app = FastAPI()
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])
    app.mount("/vendor", StaticFiles(directory=Path(__file__).with_name("vendor")), name="vendor")

    @app.get("/")
    @app.get("/graph")
    def index():
        return FileResponse(Path(__file__).with_name("source_graph.html"))

    @app.get("/connection")
    def connection(request: Request):
        if request.headers.get("sec-fetch-site") == "cross-site":
            raise HTTPException(403)
        return {"key": view.key, "coding_url": view.upstream}

    @app.get("/graph-state")
    def state(request: Request):
        if request.headers.get("x-demo-key") != view.key:
            raise HTTPException(403)
        try:
            return view.snapshot()
        except (httpx.HTTPError, RuntimeError) as error:
            raise HTTPException(503, str(error)) from error

    return app


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream", default="http://127.0.0.1:8907")
    parser.add_argument("--port", type=int, default=8927)
    args = parser.parse_args()
    view = SourceView(args.upstream, Path.home() / ".local/share/midflight-demo")
    uvicorn.run(create_app(view), host="127.0.0.1", port=args.port, access_log=False)


if __name__ == "__main__":
    main()
