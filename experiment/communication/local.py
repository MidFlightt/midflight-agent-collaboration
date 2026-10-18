"""Prepare fresh local credentials and TLS. Never starts agents, Docker or a backend."""

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path

from experiment.communication.case import DEPENDENCIES, OWNERS
from midflight.communication.provision import provision

ROOT = Path(__file__).resolve().parents[2]


def prepare_local(project, credentials, *, root=ROOT):
    if not re.fullmatch(r"[A-Za-z0-9]{1,40}", project):
        raise ValueError("Use a new alphanumeric project ID, at most 40 characters")
    root, credentials = root.resolve(), credentials.expanduser().resolve()
    if credentials.is_relative_to(root):
        raise ValueError("Credentials must be outside this checkout")
    backend = root / "runs/local-backend"
    if backend.exists() or credentials.exists():
        raise FileExistsError(
            "Existing local setup preserved; use a fresh checkout/project directory"
        )
    openssl = shutil.which("openssl")
    if not openssl:
        raise RuntimeError("OpenSSL with -addext support is required")
    provision(project, DEPENDENCIES, OWNERS, credentials)
    backend.mkdir(parents=True, mode=0o700)
    key, cert = backend / "key.pem", backend / "cert.pem"
    # Keep startup failures and credentials for inspection; never overwrite a prior setup.
    with (backend / "tls-setup.log").open("x") as log:
        subprocess.run(
            [
                openssl,
                "req",
                "-x509",
                "-newkey",
                "rsa:2048",
                "-sha256",
                "-nodes",
                "-days",
                "30",
                "-subj",
                "/CN=localhost",
                "-addext",
                "subjectAltName=IP:127.0.0.1,DNS:localhost",
                "-keyout",
                str(key),
                "-out",
                str(cert),
            ],
            check=True,
            stdout=log,
            stderr=log,
        )
    key.chmod(0o600)
    (backend / "setup.json").write_text(
        json.dumps(
            {
                "project": project,
                "credentials_directory": str(credentials),
                "endpoint": "https://127.0.0.1:19483",
                "db_port": 52017,
                "status": "prepared; no services or agents started",
            },
            indent=2,
        )
    )
    return backend


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--credentials", required=True, type=Path)
    args = parser.parse_args()
    directory = prepare_local(args.project, args.credentials)
    print(f"Prepared private credentials and TLS in {directory}. No services/agents started.")
