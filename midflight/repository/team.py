"""The team server: the hosted connector on FalkorDB, run once by a team's administrator.

Teammates on other computers add its HTTPS address to their coding client and sign in
with GitHub; each person gets only their own short-lived token (D17), and the project's
join code makes them a member (D18). Nothing here is shared between people: no setup
key, no copied credentials. The server itself listens only on 127.0.0.1; an HTTPS
reverse proxy or tunnel on the same computer publishes it.
"""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse

import httpx

from midflight.config import Settings

TEAM_PORT = 8100
TEAM_GRAPH = "midflight-team"
SECRETS = {
    "MIDFLIGHT_GITHUB_CLIENT_ID": "the GitHub App's Client ID",
    "MIDFLIGHT_GITHUB_CLIENT_SECRET": "a client secret generated in the GitHub App",
    "MIDFLIGHT_GITHUB_APP_ID": "the GitHub App's App ID",
    "MIDFLIGHT_GITHUB_PRIVATE_KEY_PATH": "the path of the App's downloaded .pem private key",
}
TEMPLATE = """\
# MidFlight team server settings, read by `midflight host`. Keep this file private.
# The README section "Set up a team" says where each value comes from.

# The HTTPS address teammates use, without a trailing slash.
MIDFLIGHT_PUBLIC_URL=

# Your GitHub App (Sign in with GitHub, and repository access).
MIDFLIGHT_GITHUB_CLIENT_ID=
MIDFLIGHT_GITHUB_CLIENT_SECRET=
MIDFLIGHT_GITHUB_APP_ID=
MIDFLIGHT_GITHUB_PRIVATE_KEY_PATH=

# Optional: the App's webhook secret, for midflight/verify checks on pushes.
MIDFLIGHT_GITHUB_WEBHOOK_SECRET=
"""


def read_env_file(path: Path) -> dict[str, str]:
    values = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def team_settings(env_file: Path, url: str | None, db_port: int, graph: str) -> Settings:
    """Settings from the private file (environment variables win), or a clear next step."""
    from midflight.repository.cli import private_write

    if not env_file.exists():
        private_write(env_file, TEMPLATE)
        raise ValueError(
            f"Created {env_file}. Fill in your public URL and GitHub App values "
            '(README: "Set up a team"), then rerun `midflight host`.'
        )
    if env_file.stat().st_mode & 0o077:
        raise ValueError(f"{env_file} is readable by other users. Run: chmod 600 {env_file}")
    env = read_env_file(env_file) | {
        k: v for k, v in os.environ.items() if k.startswith("MIDFLIGHT_")
    }
    if url:
        env["MIDFLIGHT_PUBLIC_URL"] = url
    if env.get("MIDFLIGHT_DEV_LOGIN") == "1":
        raise ValueError("A team server never uses MIDFLIGHT_DEV_LOGIN; remove it.")
    public = urlparse(env.get("MIDFLIGHT_PUBLIC_URL", ""))
    if public.scheme != "https" or public.hostname in {None, "127.0.0.1", "localhost"}:
        raise ValueError(
            "MIDFLIGHT_PUBLIC_URL must be the HTTPS address teammates reach, for example "
            "https://midflight.example.com (README: 'A public HTTPS address'). "
            "For one computer, use `midflight up` instead."
        )
    missing = [f"{key} ({what})" for key, what in SECRETS.items() if not env.get(key)]
    if missing:
        raise ValueError(f"Fill in {env_file}:\n  " + "\n  ".join(missing))
    key_path = Path(env["MIDFLIGHT_GITHUB_PRIVATE_KEY_PATH"]).expanduser()
    if not key_path.is_file():
        raise ValueError(f"The GitHub App private key {key_path} doesn't exist.")
    env |= {
        "MIDFLIGHT_STORE": "falkordb",
        "MIDFLIGHT_FALKOR_PORT": str(db_port),
        "MIDFLIGHT_FALKOR_GRAPH": graph,
    }
    return Settings.from_env(env)


def connect_commands(public_url: str) -> list[str]:
    mcp = f"{public_url}/mcp"
    return [
        f"claude mcp add --transport http --scope user midflight {mcp}",
        f"codex mcp add midflight --url {mcp}",  # opens the browser to sign in
    ]


def describe(settings: Settings, env_file: Path) -> None:
    url = settings.public_url
    try:
        reachable = httpx.get(f"{url}/healthz", timeout=5).status_code == 200
    except httpx.HTTPError:
        reachable = False
    print(f"✓ Settings in {env_file}")
    print(f"✓ GitHub App {settings.github_app_id} configured")
    print(
        ("✓ " if reachable else "• ")
        + f"{url} "
        + ("answers" if reachable else "isn't answering yet")
    )
    print(f"\nGitHub App callback URL: {url}/oauth/github/callback")
    print("Teammates connect with one of:")
    for command in connect_commands(url):
        print(f"    {command}")


def host(args) -> None:
    import uvicorn

    from midflight.main import create_server
    from midflight.repository.cli import ensure_falkordb, port_in_use

    settings = team_settings(args.env_file, args.url, args.db_port, args.graph)
    if args.check:
        describe(settings, args.env_file)
        return
    if port_in_use(args.port):
        raise ValueError(
            f"Port {args.port} is already in use; is `midflight host` already running? "
            "Otherwise pass --port and point your HTTPS proxy at it."
        )
    ensure_falkordb(args.db_port)
    server = create_server(settings)
    print(f"MidFlight team server on 127.0.0.1:{args.port} (graph {args.graph})")
    print(f"Publish it at {settings.public_url} with your HTTPS proxy or tunnel.")
    for command in connect_commands(settings.public_url):
        print(f"    {command}")
    uvicorn.run(server.app, host="127.0.0.1", port=args.port)
