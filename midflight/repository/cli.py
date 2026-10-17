"""Local-first setup for real repositories. Credentials never go in generated MCP arguments."""

from __future__ import annotations

import argparse
import json
import os
import secrets
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

import httpx

from midflight.repository.instructions import END, INSTRUCTIONS, START

DEFAULT_HOME = Path.home() / ".local/share/midflight"


def private_write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    # Exclusive creation refuses both overwrites and symlink traversal at the filename.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as output:
        output.write(value)


def local_url(url):
    parsed = urlparse(url)
    if (
        parsed.scheme != "http"
        or parsed.hostname not in {"127.0.0.1", "localhost"}
        or parsed.username
        or parsed.password
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Local setup requires an http://127.0.0.1:PORT or localhost URL")
    return url.rstrip("/")


def initialize(repo, url, repository, agents, home):
    repo = repo.resolve()
    subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--show-toplevel"], check=True, capture_output=True
    )
    top = subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "--show-toplevel"], text=True
    ).strip()
    if Path(top).resolve() != repo:
        raise ValueError("Pass the Git repository root, not a subdirectory")
    for name in (".midflight", "AGENTS.md", ".gitignore"):
        if (repo / name).is_symlink():
            raise ValueError(f"Refusing to write through repository symlink: {name}")
    url = local_url(url)
    names = ["lead", *agents]
    if len(names) != len(set(names)):
        raise ValueError("Agent names must be unique and must not include lead")
    # Validate before creating files or contacting the service.
    from midflight.repository.server import Bootstrap, Identity

    manifest = Bootstrap(
        project_id="local-" + secrets.token_hex(8),
        repository=repository,
        identities=[Identity(name=n, token=secrets.token_urlsafe(32)) for n in names],
    )
    private = repo / ".midflight/private.json"
    if private.is_symlink():
        raise ValueError("Refusing a symlinked private configuration")
    if private.exists():
        config = json.loads(private.read_text())
        if (
            config["url"] != url
            or config["repository"] != repository
            or set(config["identities"]) != set(names)
        ):
            raise ValueError(
                "Existing setup differs. Reuse its URL, repository and identity names; "
                "it was not overwritten."
            )
    else:
        ignore = repo / ".gitignore"
        with ignore.open("a") as output:
            output.write("\n# MidFlight local credentials and client configuration\n/.midflight/\n")
        config = {
            "url": url,
            "repository": repository,
            "project_id": manifest.project_id,
            "identities": {
                i.name: {
                    "id": f"{manifest.project_id}.{i.name}",
                    "token": i.token,
                    "role": "lead" if i.name == "lead" else "agent",
                }
                for i in manifest.identities
            },
        }
        # Save before HTTP: a lost bootstrap response can be retried with the same identities.
        private_write(private, json.dumps(config, indent=2))
    body = {
        "project_id": config["project_id"],
        "repository": repository,
        "identities": [
            {"name": name, "token": data["token"]} for name, data in config["identities"].items()
        ],
    }
    key = (home / "setup.key").read_text().strip()
    with httpx.Client(timeout=30) as client:
        response = client.post(
            url + "/local/projects", json=body, headers={"Authorization": "Bearer " + key}
        )
        if response.is_error:
            raise ValueError(
                f"Setup refused (HTTP {response.status_code}); files retained for retry. "
                "Check the service URL, local setup key and repository identity."
            )
    instructions = repo / "AGENTS.md"
    existing = instructions.read_text() if instructions.exists() else ""
    if START not in existing:
        with instructions.open("a") as output:
            output.write("\n" + START + "\n" + INSTRUCTIONS + END + "\n")
    elif END not in existing:
        raise ValueError(
            "Incomplete MidFlight instruction block; repair AGENTS.md before continuing"
        )
    for name in names:
        snippet = repo / ".midflight" / f"mcp-{name}.json"
        value = {
            "mcpServers": {
                "midflight": {
                    "command": sys.executable,
                    "args": [
                        "-m",
                        "midflight.repository.cli",
                        "mcp",
                        "--repo",
                        str(repo),
                        "--identity",
                        name,
                    ],
                }
            }
        }
        if not snippet.exists():
            private_write(snippet, json.dumps(value, indent=2))
    from midflight.repository.workspace import install_start_guide

    install_start_guide(repo, config)
    return config


def serve(args):
    import uvicorn

    from midflight.config import Settings
    from midflight.main import create_server
    from midflight.repository.server import add_local_routes

    args.home.mkdir(parents=True, exist_ok=True, mode=0o700)
    keyfile = args.home / "setup.key"
    if not keyfile.exists():
        private_write(keyfile, secrets.token_urlsafe(48))
    server = create_server(
        Settings(
            dev_login=True,
            store_backend="falkordb",
            falkor_port=args.db_port,
            falkor_graph=args.graph,
            public_url=f"http://127.0.0.1:{args.port}",
        )
    )
    add_local_routes(server, keyfile.read_text().strip())
    print(f"MidFlight local service: http://127.0.0.1:{args.port}; graph={args.graph}")
    uvicorn.run(server.app, host="127.0.0.1", port=args.port)


def codex_command(
    repo: Path, identity: str, prompt: str | None = None, approve_tools: bool = False
):
    # Invocation-only overrides; no auth, trust, sandbox or global config changes.
    args = ["-m", "midflight.repository.cli", "mcp", "--repo", str(repo), "--identity", identity]
    config = (
        "mcp_servers.midflight_repository={command="
        + json.dumps(sys.executable)
        + ",args="
        + json.dumps(args)
        + "}"
    )
    policies = []
    if approve_tools:
        for tool in (
            "project_context",
            "get_plan",
            "check_in",
            "submit_claim",
            "acknowledge_directive",
        ):
            policies += [
                "-c",
                f'mcp_servers.midflight_repository.tools.{tool}.approval_mode="approve"',
            ]
    return [
        "codex",
        *(["exec", "-s", "workspace-write"] if prompt is not None else []),
        "-C",
        str(repo),
        "-c",
        config,
        *policies,
        *([prompt] if prompt is not None else []),
    ]


def main():
    parser = argparse.ArgumentParser(
        description="Connect a real repository to local FalkorDB-backed MidFlight"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    service = sub.add_parser(
        "serve", help="Run one persistent local service, without the demo seed"
    )
    service.add_argument("--port", type=int, default=8000)
    service.add_argument("--db-port", type=int, default=6379)
    service.add_argument("--graph", default="midflight-local")
    service.add_argument("--home", type=Path, default=DEFAULT_HOME)
    init = sub.add_parser("init", help="Install once in an existing Git repository")
    init.add_argument("--repo", type=Path, required=True)
    init.add_argument(
        "--repository", required=True, help="Repository identity owner/name; no GitHub App required"
    )
    init.add_argument("--agents", default="backend,frontend,tests")
    init.add_argument("--url", default="http://127.0.0.1:8000")
    init.add_argument("--home", type=Path, default=DEFAULT_HOME)
    for command in ("mcp", "doctor", "agent"):
        child = sub.add_parser(command)
        child.add_argument("--repo", type=Path, required=True)
        child.add_argument("--identity", default="lead")
        if command == "agent":
            child.add_argument(
                "--approve-coordination-tools",
                action="store_true",
                help="Approve local coordination tools for this session; excludes plan writes",
            )
            child.add_argument(
                "--exec", dest="exec_prompt", help="Optional headless acceptance run"
            )
    args = parser.parse_args()
    try:
        if args.command == "serve":
            serve(args)
        elif args.command == "init":
            config = initialize(
                args.repo,
                args.url,
                args.repository,
                args.agents.split(",") if args.agents else [],
                args.home,
            )
            print(
                f"Connected {config['repository']} as {config['project_id']}. "
                "Installed AGENTS.md instructions. Open MIDFLIGHT.md to start."
            )
            print(
                "Configure each MCP client using .midflight/mcp-<identity>.json. "
                "Start with project_context."
            )
        elif args.command == "agent":
            config = json.loads((args.repo / ".midflight/private.json").read_text())
            if args.identity not in config["identities"]:
                raise ValueError("Unknown identity; use one created by init")
            command = codex_command(
                args.repo.resolve(),
                args.identity,
                args.exec_prompt,
                args.approve_coordination_tools,
            )
            os.execvp(command[0], command)
        elif args.command == "mcp":
            from midflight.repository.mcp import run

            run(args.repo.resolve(), args.identity)
        else:
            from midflight.mcp.local.client import MidflightApi

            config = json.loads((args.repo / ".midflight/private.json").read_text())
            member = config["identities"][args.identity]
            api = MidflightApi.connect(
                local_url(config["url"]), member["token"], config["project_id"]
            )
            try:
                data = api._call("GET", f"/local/projects/{config['project_id']}")
            finally:
                api._http.close()
            print(json.dumps(data, indent=2))
    except (OSError, ValueError, KeyError, httpx.HTTPError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"MidFlight setup failed: {type(error).__name__}. {error}\n")


if __name__ == "__main__":
    main()
