"""Local-first setup for real repositories. Credentials never go in generated MCP arguments."""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import httpx
from pydantic import ValidationError

from midflight.mcp.local.client import MidflightUnavailable, NotSignedIn
from midflight.repository.instructions import END, INSTRUCTIONS, START

DEFAULT_HOME = Path.home() / ".local/share/midflight"
DEFAULT_URL = "http://127.0.0.1:8000"
DEFAULT_DB_PORT = 6379
# Preapprovable with --approve-coordination-tools; plan writes are never in this list.
COORDINATION_TOOLS = (
    "project_context",
    "get_plan",
    "check_in",
    "submit_claim",
    "acknowledge_directive",
)
# Files init adds to the repository that worktrees need committed.
SHARED_FILES = ("AGENTS.md", ".gitignore", ".mcp.json", "MIDFLIGHT.md")


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


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)


def git_root(path):
    result = git(path, "rev-parse", "--show-toplevel")
    if result.returncode:
        raise ValueError(f"{path} is not inside a Git repository. Run `git init` there first.")
    return Path(result.stdout.strip()).resolve()


def default_repository(repo):
    """owner/name from the origin remote, else local/<folder>. Only used as a label locally."""
    remote = git(repo, "remote", "get-url", "origin").stdout.strip()
    match = re.search(r"[:/]([\w.-]+)/([\w.-]+?)(?:\.git)?/?$", remote)
    if match:
        return f"{match[1]}/{match[2]}"
    return "local/" + (re.sub(r"[^\w.-]", "-", repo.name) or "repo")


def default_identity(repo):
    """`midflight worktree` records each worktree's identity; the main checkout is the lead."""
    marker = repo / ".midflight/identity"
    return marker.read_text().strip() if marker.is_file() else "lead"


def load_config(repo):
    private = repo / ".midflight/private.json"
    if not private.is_file():
        raise ValueError(
            f"{repo} is not connected to MidFlight yet. Run `midflight up` (or `midflight init`) "
            "in it."
        )
    return json.loads(private.read_text())


def member(config, identity):
    if identity not in config["identities"]:
        raise ValueError(
            f"Unknown identity {identity!r}. Choose one of: {', '.join(config['identities'])}."
        )
    return config["identities"][identity]


def write_snippet(repo, name):
    """Machine-local MCP client config for one identity; absolute paths, no token."""
    snippet = repo / ".midflight" / f"mcp-{name}.json"
    if not snippet.exists():
        args = ["-m", "midflight.repository.cli", "mcp", "--repo", str(repo), "--identity", name]
        value = {"mcpServers": {"midflight": {"command": sys.executable, "args": args}}}
        private_write(snippet, json.dumps(value, indent=2))
    return snippet


def registered(client, config):
    """Whether the service knows the saved lead credentials."""
    response = client.get(
        config["url"] + f"/local/projects/{config['project_id']}",
        headers={"Authorization": "Bearer " + config["identities"]["lead"]["token"]},
    )
    if response.status_code == 401:
        return False
    response.raise_for_status()
    return True


def initialize(repo, url, repository, agents, home):
    repo = repo.resolve()
    if git_root(repo) != repo:
        raise ValueError("Pass the Git repository root, not a subdirectory")
    for name in (".midflight", "AGENTS.md", ".gitignore", ".mcp.json"):
        if (repo / name).is_symlink():
            raise ValueError(f"Refusing to write through repository symlink: {name}")
    url = local_url(url)
    names = ["lead", *agents]
    if len(names) != len(set(names)):
        raise ValueError("Agent names must be unique and must not include lead")
    # Validate before creating files or contacting the service.
    from midflight.repository.server import Bootstrap, Identity

    try:
        manifest = Bootstrap(
            project_id="local-" + secrets.token_hex(8),
            repository=repository,
            identities=[Identity(name=n, token=secrets.token_urlsafe(32)) for n in names],
        )
    except ValidationError:
        raise ValueError(
            "--repository must look like owner/name, and agent names use lowercase letters, "
            "digits and hyphens (for example backend,frontend)."
        ) from None
    keyfile = home / "setup.key"
    if not keyfile.is_file():
        raise ValueError(
            f"No local setup key at {keyfile}. Start the service first with `midflight up` "
            "(or `midflight serve`), using the same --home."
        )
    key = keyfile.read_text().strip()
    private = repo / ".midflight/private.json"
    if private.is_symlink():
        raise ValueError("Refusing a symlinked private configuration")
    with httpx.Client(timeout=30) as client:
        try:
            client.get(url + "/healthz")
        except httpx.TransportError:
            raise ValueError(
                f"The MidFlight service isn't running at {url}. Start it with `midflight up`."
            ) from None
        # Nothing has been written yet, so a failure above leaves the repository untouched.
        config = json.loads(private.read_text()) if private.exists() else None
        if config:
            differs = [k for k, v in (("url", url), ("repository", repository)) if config[k] != v]
            if set(config["identities"]) != set(names):
                differs.append("agents")
            if differs and config["url"] == url and not registered(client, config):
                private.unlink()  # The service never accepted it, so starting over is safe.
                config = None
            elif differs:
                agents_saved = ", ".join(n for n in config["identities"] if n != "lead")
                raise ValueError(
                    f"This repository is already connected with a different {', '.join(differs)} "
                    f"(saved: url {config['url']}, repository {config['repository']}, "
                    f"agents {agents_saved}). Rerun with the saved values; adding agents to an "
                    "existing project isn't supported yet. Nothing was changed."
                )
        if config is None:
            ignore = repo / ".gitignore"
            if "/.midflight/" not in (ignore.read_text() if ignore.exists() else ""):
                with ignore.open("a") as output:
                    output.write(
                        "\n# MidFlight local credentials and client configuration\n/.midflight/\n"
                    )
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
                {"name": name, "token": data["token"]}
                for name, data in config["identities"].items()
            ],
        }
        response = client.post(
            url + "/local/projects", json=body, headers={"Authorization": "Bearer " + key}
        )
        if response.is_error:
            try:
                detail = response.json().get("detail", "")
            except ValueError:
                detail = response.text
            raise ValueError(
                f"Setup refused (HTTP {response.status_code}): {detail}. Files retained for "
                "retry. Check that the service uses the same --home as init."
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
        write_snippet(repo, name)
    from midflight.repository.workspace import install_client_config, install_start_guide

    install_client_config(repo)
    install_start_guide(repo, config)
    return config


def add_worktree(repo, identity, path=None, branch=None):
    """A separate checkout for one agent, with its credentials and identity in place."""
    config = load_config(repo)
    member(config, identity)
    if identity == "lead":
        raise ValueError("The lead works in the main checkout; create worktrees for agents.")
    files = [f for f in SHARED_FILES if (repo / f).exists()]
    if git(repo, "status", "--porcelain", "--", *files).stdout.strip():
        raise ValueError(
            "Commit the MidFlight files first so the worktree gets them:\n"
            f"    git add {' '.join(files)} && git commit -m 'Connect MidFlight'"
        )
    path = Path(path or repo.parent / f"{repo.name}-{identity}").resolve()
    branch = branch or f"{identity}-work"
    exists = git(repo, "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}").returncode == 0
    command = [str(path), branch] if exists else ["-b", branch, str(path)]
    result = git(repo, "worktree", "add", *command)
    if result.returncode:
        raise ValueError(f"git worktree add failed: {result.stderr.strip()}")
    private_write(path / ".midflight/private.json", (repo / ".midflight/private.json").read_text())
    (path / ".midflight/identity").write_text(identity + "\n")
    write_snippet(path, identity)
    return path


def falkordb_state(port):
    """'ok', 'down', 'not-falkordb' or 'no-client' for the database on this port."""
    try:
        import redis
    except ImportError:
        return "no-client"
    client = redis.Redis(port=port, socket_connect_timeout=1, socket_timeout=2)
    try:
        client.execute_command("GRAPH.LIST")
        return "ok"
    except redis.exceptions.ConnectionError:
        return "down"
    except redis.exceptions.ResponseError:
        return "not-falkordb"
    finally:
        client.close()


def compose_file():
    # Bundled in the wheel beside the package; at the repository root in a source checkout.
    here = Path(__file__).resolve()
    for candidate in (here.parents[1], here.parents[2]):
        if (candidate / "compose.graph-hacks.yml").is_file():
            return candidate / "compose.graph-hacks.yml"
    raise ValueError("The bundled FalkorDB Compose file is missing; reinstall MidFlight.")


def require_falkordb(port):
    state = falkordb_state(port)
    if state == "no-client":
        raise ValueError(
            "The FalkorDB client isn't installed. Install MidFlight with its falkordb extra "
            '(uv tool install "midflight[falkordb] @ git+…").'
        )
    if state == "not-falkordb":
        raise ValueError(
            f"Port {port} answers but isn't FalkorDB (another Redis?). Stop it, or start "
            "FalkorDB on another port and pass --db-port."
        )
    if state == "down" and port != DEFAULT_DB_PORT:
        raise ValueError(f"FalkorDB isn't reachable on 127.0.0.1:{port}. Start it on that port.")
    if state == "down":
        raise ValueError(f"FalkorDB isn't reachable on 127.0.0.1:{port}. Run `midflight up`.")


def ensure_falkordb(port):
    if falkordb_state(port) == "down" and port == DEFAULT_DB_PORT:
        if not shutil.which("docker"):
            raise ValueError(
                "FalkorDB isn't running and Docker isn't installed. Install Docker, or start "
                f"FalkorDB on 127.0.0.1:{port} yourself, then retry."
            )
        print("Starting FalkorDB with Docker…")
        result = subprocess.run(
            ["docker", "compose", "-f", str(compose_file()), "up", "-d", "--wait"],
            capture_output=True,
            text=True,
        )
        if result.returncode:
            raise ValueError(
                "Couldn't start FalkorDB with Docker. Is Docker running, and is port "
                f"{port} free?\n{result.stderr.strip()[-800:]}"
            )
    require_falkordb(port)


def service_ready(url):
    try:
        return httpx.get(url + "/healthz", timeout=2).status_code == 200
    except httpx.TransportError:
        return False


def port_in_use(port):
    with socket.socket() as probe:
        return probe.connect_ex(("127.0.0.1", port)) == 0


def serve_args(args):
    return [
        *("--port", str(args.port), "--db-port", str(args.db_port)),
        *("--graph", args.graph, "--home", str(args.home)),
    ]


def ensure_service(args):
    url = f"http://127.0.0.1:{args.port}"
    if service_ready(url):
        return url
    if port_in_use(args.port):
        raise ValueError(
            f"Port {args.port} is used by another program. Pass --port to choose another."
        )
    args.home.mkdir(parents=True, exist_ok=True, mode=0o700)
    log = args.home / "serve.log"
    with log.open("a") as output:
        process = subprocess.Popen(
            [sys.executable, "-m", "midflight.repository.cli", "serve", *serve_args(args)],
            stdin=subprocess.DEVNULL,
            stdout=output,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    (args.home / "serve.pid").write_text(str(process.pid))
    for _ in range(60):
        if service_ready(url):
            return url
        if process.poll() is not None:
            raise ValueError(f"The service stopped during startup. See {log}")
        time.sleep(0.5)
    raise ValueError(f"The service didn't answer within 30 seconds. See {log}")


def up(args):
    ensure_falkordb(args.db_port)
    url = ensure_service(args)
    print(f"✓ FalkorDB on 127.0.0.1:{args.db_port}")
    print(f"✓ MidFlight service at {url} (log: {args.home / 'serve.log'})")
    try:
        repo = args.repo.resolve() if args.repo else git_root(Path.cwd())
    except ValueError:
        print("\nNext: run `midflight up` again inside your application's Git repository.")
        return
    if not (repo / ".midflight/private.json").exists():
        repository = args.repository or default_repository(repo)
        config = initialize(repo, url, repository, split_agents(args.agents), args.home)
        print(
            f"✓ Connected {config['repository']} with identities: {', '.join(config['identities'])}"
        )
    else:
        print(f"✓ {repo.name} is already connected")
    print(f"\nNext: open {repo / 'MIDFLIGHT.md'}, or start the lead here with `midflight agent`.")


def stop_service(home):
    pidfile = home / "serve.pid"
    if not pidfile.is_file():
        return False
    pid = int(pidfile.read_text())
    pidfile.unlink()
    command = subprocess.run(
        ["ps", "-p", str(pid), "-o", "command="], capture_output=True, text=True
    )
    if "midflight.repository.cli serve" not in command.stdout:
        return False  # Already gone, or the PID now belongs to something else.
    os.kill(pid, signal.SIGTERM)
    for _ in range(20):
        if subprocess.run(["ps", "-p", str(pid)], capture_output=True).returncode:
            break
        time.sleep(0.25)
    return True


def down(args):
    if stop_service(args.home):
        print("Stopped the MidFlight service.")
    else:
        print("No background MidFlight service was running (stop `midflight serve` with Ctrl+C).")
    if args.db:
        subprocess.run(["docker", "compose", "-f", str(compose_file()), "stop"], check=True)
        print("Stopped FalkorDB. Its data volume is kept.")


def status(args, repo):
    """Pass/fail checks, each with the fix; exit status 1 if any fails."""
    from midflight.mcp.local.client import MidflightApi

    def check(ok, label, fix=""):
        print(("✓ " if ok else "✗ ") + label + ("" if ok or not fix else f"\n    → {fix}"))
        return ok

    db = falkordb_state(args.db_port)
    ok = check(db == "ok", f"FalkorDB on 127.0.0.1:{args.db_port}", "Run `midflight up`.")
    private = repo / ".midflight/private.json"
    config = json.loads(private.read_text()) if private.is_file() else None
    url = config["url"] if config else DEFAULT_URL
    if not check(service_ready(url), f"MidFlight service at {url}", "Run `midflight up`."):
        return False
    if not check(config is not None, f"{repo.name} connected", "Run `midflight up` here."):
        return False
    identity = args.identity or default_identity(repo)
    data = member(config, identity)
    api = MidflightApi.connect(local_url(url), data["token"], config["project_id"])
    try:
        context = api._call("GET", f"/local/projects/{config['project_id']}")
    except (NotSignedIn, MidflightUnavailable) as error:
        return check(
            False,
            f"Credentials for {identity}",
            f"{error}. The service may be using a different database than when you ran init "
            "(another --graph, or a different Docker volume).",
        )
    finally:
        api._http.close()
    if args.json:
        print(json.dumps(context, indent=2))
        return ok
    check(True, f"Signed in as {identity} ({data['role']}) in {config['repository']}")
    names = ", ".join(m["name"] for m in context["members"])
    print(f"  members: {names}")
    plan = context["plan"]
    if plan:
        check(True, f"Plan v{plan['version']} ({plan['status']})")
    else:
        print("• No plan yet: describe your application to the lead and ask it to propose one.")
    return ok


def serve(args):
    import uvicorn

    from midflight.config import Settings
    from midflight.main import create_server
    from midflight.repository.server import add_local_routes

    if port_in_use(args.port):
        raise ValueError(
            f"Port {args.port} is already in use. If MidFlight is already running, check it with "
            "`midflight status`; otherwise pass --port."
        )
    require_falkordb(args.db_port)
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
    repo: Path,
    identity: str,
    prompt: str | None = None,
    approve_tools: bool = False,
    extra=(),
):
    # Invocation-only overrides; no auth, trust, sandbox or global config changes.
    args = ["-m", "midflight.repository.cli", "mcp", "--repo", str(repo), "--identity", identity]
    config = (
        "mcp_servers.midflight={command="
        + json.dumps(sys.executable)
        + ",args="
        + json.dumps(args)
        + "}"
    )
    policies = []
    if approve_tools:
        for tool in COORDINATION_TOOLS:
            policies += ["-c", f'mcp_servers.midflight.tools.{tool}.approval_mode="approve"']
    return [
        "codex",
        *(["exec", "-s", "workspace-write"] if prompt is not None else []),
        "-C",
        str(repo),
        "-c",
        config,
        *policies,
        *extra,
        *([prompt] if prompt is not None else []),
    ]


def claude_command(
    repo: Path,
    identity: str,
    prompt: str | None = None,
    approve_tools: bool = False,
    extra=(),
):
    # Adds this identity's server for the session; the client's own settings stay in force.
    command = ["claude", *(["-p", prompt] if prompt is not None else [])]
    command += ["--mcp-config", str(write_snippet(repo, identity))]
    if approve_tools:
        command += ["--allowedTools", ",".join(f"mcp__midflight__{t}" for t in COORDINATION_TOOLS)]
    return [*command, *extra]


def split_agents(value):
    return [a.strip() for a in value.split(",") if a.strip()] if value else []


def explain(error):
    if isinstance(error, NotSignedIn):
        return (
            f"The service rejected these credentials ({error}). It may be using a different "
            "database than when you ran init; run `midflight status`."
        )
    if isinstance(error, (MidflightUnavailable, httpx.TransportError)):
        return "Can't reach the MidFlight service. Start it with `midflight up`."
    if isinstance(error, subprocess.CalledProcessError):
        return f"`{' '.join(map(str, error.cmd))}` failed with exit status {error.returncode}."
    return str(error)


def main():
    parser = argparse.ArgumentParser(
        description="Connect a real repository to local FalkorDB-backed MidFlight"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def service_options(command):
        command.add_argument("--port", type=int, default=8000)
        command.add_argument("--db-port", type=int, default=DEFAULT_DB_PORT)
        command.add_argument("--graph", default="midflight-local")
        command.add_argument("--home", type=Path, default=DEFAULT_HOME)

    repo_help = "Git repository (default: the one containing the current directory)"
    identity_help = "Identity (default: this worktree's, or lead in the main checkout)"
    start = sub.add_parser(
        "up", help="Start FalkorDB and the service if needed, then connect this repository"
    )
    service_options(start)
    start.add_argument("--repo", type=Path, help=repo_help)
    start.add_argument("--repository", help="owner/name label (default: from the git remote)")
    start.add_argument("--agents", default="backend,frontend,tests")
    stop = sub.add_parser("down", help="Stop the background service started by `up`")
    stop.add_argument("--home", type=Path, default=DEFAULT_HOME)
    stop.add_argument("--db", action="store_true", help="Also stop FalkorDB; its data is kept")
    service = sub.add_parser(
        "serve", help="Run one persistent local service in the foreground, without the demo seed"
    )
    service_options(service)
    init = sub.add_parser("init", help="Install once in an existing Git repository")
    init.add_argument("--repo", type=Path, help=repo_help)
    init.add_argument("--repository", help="owner/name label (default: from the git remote)")
    init.add_argument("--agents", default="backend,frontend,tests")
    init.add_argument("--url", default=DEFAULT_URL)
    init.add_argument("--home", type=Path, default=DEFAULT_HOME)
    worktree = sub.add_parser("worktree", help="Create a Git worktree for one agent identity")
    worktree.add_argument("identity")
    worktree.add_argument("path", nargs="?", type=Path)
    worktree.add_argument("--repo", type=Path, help=repo_help)
    worktree.add_argument("--branch")
    for command in ("mcp", "status", "doctor", "agent"):
        child = sub.add_parser(command, help="Same as status" if command == "doctor" else None)
        child.add_argument("--repo", type=Path, help=repo_help)
        child.add_argument("--identity", help=identity_help)
        if command in ("status", "doctor"):
            child.add_argument("--db-port", type=int, default=DEFAULT_DB_PORT)
            child.add_argument("--json", action="store_true", help="Print raw project context")
        if command == "agent":
            child.add_argument("--client", choices=("codex", "claude"), default="codex")
            child.add_argument(
                "--approve-coordination-tools",
                action="store_true",
                help="Approve local coordination tools for this session; excludes plan writes",
            )
            child.add_argument(
                "--exec", dest="exec_prompt", help="Optional headless acceptance run"
            )
    argv, extra = sys.argv[1:], []
    if "--" in argv:  # `midflight agent -- -m MODEL` passes everything after -- to the client.
        argv, extra = argv[: argv.index("--")], argv[argv.index("--") + 1 :]
    args = parser.parse_args(argv)
    if extra and args.command != "agent":
        parser.error("Only `agent` passes arguments after -- to the coding client")
    try:
        if args.command == "up":
            up(args)
        elif args.command == "down":
            down(args)
        elif args.command == "serve":
            serve(args)
        elif args.command == "init":
            repo = args.repo or git_root(Path.cwd())
            config = initialize(
                repo,
                args.url,
                args.repository or default_repository(repo.resolve()),
                split_agents(args.agents),
                args.home,
            )
            print(
                f"Connected {config['repository']} as {config['project_id']}. "
                "Installed AGENTS.md instructions. Open MIDFLIGHT.md to start."
            )
        elif args.command == "worktree":
            repo = args.repo.resolve() if args.repo else git_root(Path.cwd())
            path = add_worktree(repo, args.identity, args.path, args.branch)
            print(f"Created {path} for {args.identity}. Start it with:")
            print(f"    cd {path} && midflight agent")
        else:
            repo = args.repo.resolve() if args.repo else git_root(Path.cwd())
            identity = args.identity or default_identity(repo)
            if args.command == "mcp":
                from midflight.repository.mcp import run

                run(repo, identity)
            elif args.command == "agent":
                member(load_config(repo), identity)
                build = claude_command if args.client == "claude" else codex_command
                command = build(
                    repo, identity, args.exec_prompt, args.approve_coordination_tools, extra
                )
                if not shutil.which(command[0]):
                    raise ValueError(f"`{command[0]}` isn't installed or isn't on PATH.")
                os.chdir(repo)
                os.execvp(command[0], command)
            elif not status(args, repo):
                sys.exit(1)
    except (
        OSError,
        ValueError,
        KeyError,
        httpx.HTTPError,
        subprocess.CalledProcessError,
        NotSignedIn,
        MidflightUnavailable,
    ) as error:
        parser.exit(1, f"MidFlight: {explain(error)}\n")


if __name__ == "__main__":
    main()
