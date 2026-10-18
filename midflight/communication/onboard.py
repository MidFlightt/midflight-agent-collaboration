"""Install a downloaded invite bundle and start four isolated coding terminals."""

import argparse
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path
from urllib.parse import urlsplit

from .invites import AGENTS


def install(bundle, destination):
    if not isinstance(bundle, dict) or set(bundle) != {"project", "expires_at", "tokens", "url"}:
        raise ValueError("Invalid access file")
    url = urlsplit(bundle["url"])
    if (
        url.scheme != "https"
        or not url.hostname
        or url.username
        or url.password
        or url.query
        or url.fragment
        or url.path not in ("", "/")
    ):
        raise ValueError("Access file needs an HTTPS backend origin")
    if not re.fullmatch(r"invite_demo_[a-f0-9]{32}", bundle["project"]):
        raise ValueError("Invalid demo project")
    if not isinstance(bundle["expires_at"], (int, float)) or time.time() >= bundle["expires_at"]:
        raise ValueError("Demo access has expired; use a new invite")
    if (
        not isinstance(bundle["tokens"], dict)
        or set(bundle["tokens"]) != set(AGENTS)
        or any(
            not isinstance(t, str) or not re.fullmatch(r"[a-f0-9]{64}", t)
            for t in bundle["tokens"].values()
        )
    ):
        raise ValueError("Access file must contain four agent credentials")
    destination = Path(destination)
    destination.mkdir(parents=True, mode=0o700, exist_ok=False)
    for name, token in bundle["tokens"].items():
        with os.fdopen(
            os.open(destination / (name + ".token"), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600),
            "w",
        ) as f:
            f.write(token + "\n")
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--port", type=int, default=18942)
    args = parser.parse_args()
    for command in ("codex", "tmux"):
        if not shutil.which(command):
            parser.error(f"Install {command} and put it on PATH first")
    if not (Path.home() / ".codex/auth.json").exists():
        parser.error("Sign in with codex login first; this harness requires ~/.codex/auth.json")
    with socket.socket() as listener:
        try:
            listener.bind(("127.0.0.1", args.port))
        except OSError:
            parser.error("Port already in use; choose another --port")
    repo = Path(__file__).resolve().parents[2]
    suffix = uuid.uuid4().hex[:12]
    credentials = repo / "runs" / ("invite-access-" + suffix)
    root = repo / "runs" / ("invite-demo-" + suffix)
    try:
        bundle = json.loads(args.bundle.read_text())
        install(bundle, credentials)
    except (ValueError, OSError, TypeError) as error:
        parser.error(str(error))
    print(f"Open http://127.0.0.1:{args.port}/ once the server starts.", flush=True)
    print(
        "Four prompts will be unsent. Existing demos and global MCP settings stay unchanged.",
        flush=True,
    )
    subprocess.run(
        [
            sys.executable,
            "-m",
            "midflight.communication.harness",
            "--root",
            str(root),
            "--port",
            str(args.port),
            "--cloud-url",
            bundle["url"],
            "--cloud-project",
            bundle["project"],
            "--credentials",
            str(credentials),
        ],
        check=True,
    )


if __name__ == "__main__":
    main()
