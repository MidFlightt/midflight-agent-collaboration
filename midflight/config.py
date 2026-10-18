"""Settings for the Midflight server, read from environment variables.

Locally, put them in a `.env` file in the repository root (git-ignored); see
`.env.example`. On AWS, the deploy sets them (H-5).

| Variable | Meaning |
| --- | --- |
| `MIDFLIGHT_PUBLIC_URL` | Where people reach the server; locally `http://127.0.0.1:8000`. |
| `MIDFLIGHT_DEV_LOGIN` | `1` replaces Sign in with GitHub with a local form. Never on AWS. |
| `MIDFLIGHT_SEED_DEMO` | `1` loads the demo project for the local stdio adapter. |
| `MIDFLIGHT_GITHUB_CLIENT_ID` | The GitHub App's client id (sign-in). |
| `MIDFLIGHT_GITHUB_CLIENT_SECRET` | The GitHub App's client secret (sign-in). Secret. |
| `MIDFLIGHT_GITHUB_APP_ID` | The GitHub App's id (repo checks). |
| `MIDFLIGHT_GITHUB_PRIVATE_KEY_PATH` | Path to the App's `.pem` private key. Secret. |
| `MIDFLIGHT_GITHUB_PRIVATE_KEY` | The key itself, instead of a path. Secret. |
| `MIDFLIGHT_GITHUB_WEBHOOK_SECRET` | The App's webhook secret (verification). Secret. |
| `MIDFLIGHT_REVIEWER_MODEL` | Bedrock model for the AI reviewer. Unset means rules only. |
| `MIDFLIGHT_REVIEWER_ROLE_ARN` | A role in another AWS account to call Bedrock through. |
| `MIDFLIGHT_STORE` | Explicit backend: memory, dynamodb, falkordb. |
| `MIDFLIGHT_TABLE` | DynamoDB table; legacy fallback only when STORE is unset. |
| `MIDFLIGHT_SECRET_ID` | Secrets Manager secret holding the secrets above, as JSON (AWS). |
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse


@dataclass(frozen=True)
class Settings:
    public_url: str = "http://127.0.0.1:8000"
    dev_login: bool = False
    seed_demo: bool = False
    github_client_id: str | None = None
    github_client_secret: str | None = None
    github_app_id: str | None = None
    github_private_key: str | None = None
    github_webhook_secret: str | None = None
    reviewer_model: str | None = None
    reviewer_role_arn: str | None = None
    table_name: str | None = None

    store_backend: str | None = None
    falkor_host: str = "127.0.0.1"
    falkor_port: int = 6379
    falkor_graph: str = "midflight"
    falkor_username: str | None = None
    falkor_password: str | None = field(default=None, repr=False)
    falkor_ssl: bool = False
    worker_max_attempts: int = 3
    worker_poll_interval: float = 1
    worker_retry_delay: float = 2

    def __post_init__(self) -> None:
        if self.dev_login and urlparse(self.public_url).hostname not in {"127.0.0.1", "localhost"}:
            # The dev form lets anyone sign in as anyone: never reachable from other computers.
            raise ValueError("MIDFLIGHT_DEV_LOGIN only runs on a 127.0.0.1 or localhost URL")
        if self.backend not in {"memory", "dynamodb", "falkordb"}:
            raise ValueError("MIDFLIGHT_STORE must be memory, dynamodb or falkordb")
        if self.backend == "dynamodb" and not self.table_name:
            raise ValueError("DynamoDB requires MIDFLIGHT_TABLE")
        if not self.falkor_graph or not 0 < self.falkor_port < 65536:
            raise ValueError("invalid FalkorDB graph or port")
        if (
            self.worker_max_attempts < 1
            or self.worker_poll_interval <= 0
            or self.worker_retry_delay < 0
        ):
            raise ValueError("invalid worker settings")

    @property
    def backend(self) -> str:
        return self.store_backend or ("dynamodb" if self.table_name else "memory")

    @classmethod
    def from_env(
        cls,
        env: Mapping[str, str] | None = None,
        read_secret: Callable[[str], dict[str, str]] | None = None,
    ) -> Settings:
        env = dict(os.environ if env is None else env)
        if env.get("MIDFLIGHT_SECRET_ID"):
            # On AWS the secrets live in Secrets Manager, not in environment variables.
            secret = (read_secret or _read_secret)(env["MIDFLIGHT_SECRET_ID"])
            for name, value in secret.items():
                if value and value != "REPLACE_ME":
                    env.setdefault(f"MIDFLIGHT_{name.upper()}", value)
        key = env.get("MIDFLIGHT_GITHUB_PRIVATE_KEY")
        key_path = env.get("MIDFLIGHT_GITHUB_PRIVATE_KEY_PATH")
        if not key and key_path:
            key = Path(key_path).expanduser().read_text()
        return cls(
            public_url=(env.get("MIDFLIGHT_PUBLIC_URL") or cls.public_url).rstrip("/"),
            dev_login=env.get("MIDFLIGHT_DEV_LOGIN", "") == "1",
            seed_demo=env.get("MIDFLIGHT_SEED_DEMO", "") == "1",
            github_client_id=env.get("MIDFLIGHT_GITHUB_CLIENT_ID") or None,
            github_client_secret=env.get("MIDFLIGHT_GITHUB_CLIENT_SECRET") or None,
            github_app_id=env.get("MIDFLIGHT_GITHUB_APP_ID") or None,
            github_private_key=key or None,
            github_webhook_secret=env.get("MIDFLIGHT_GITHUB_WEBHOOK_SECRET") or None,
            reviewer_model=env.get("MIDFLIGHT_REVIEWER_MODEL") or None,
            reviewer_role_arn=env.get("MIDFLIGHT_REVIEWER_ROLE_ARN") or None,
            table_name=env.get("MIDFLIGHT_TABLE") or None,
            store_backend=env.get("MIDFLIGHT_STORE") or None,
            falkor_host=env.get("MIDFLIGHT_FALKOR_HOST", "127.0.0.1"),
            falkor_port=int(env.get("MIDFLIGHT_FALKOR_PORT", "6379")),
            falkor_graph=env.get("MIDFLIGHT_FALKOR_GRAPH", "midflight"),
            falkor_username=env.get("MIDFLIGHT_FALKOR_USERNAME") or None,
            falkor_password=env.get("MIDFLIGHT_FALKOR_PASSWORD") or None,
            falkor_ssl=env.get("MIDFLIGHT_FALKOR_SSL", "") == "1",
            worker_max_attempts=int(env.get("MIDFLIGHT_WORKER_MAX_ATTEMPTS", "3")),
            worker_poll_interval=float(env.get("MIDFLIGHT_WORKER_POLL_INTERVAL", "1")),
            worker_retry_delay=float(env.get("MIDFLIGHT_WORKER_RETRY_DELAY", "2")),
        )

    @property
    def github_sign_in_configured(self) -> bool:
        return bool(self.github_client_id and self.github_client_secret)

    @property
    def github_app_configured(self) -> bool:
        return bool(self.github_app_id and self.github_private_key)


def load_dotenv(path: Path = Path(".env")) -> None:
    """Copy `KEY=value` lines from a .env file into the environment, without overriding."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _read_secret(secret_id: str) -> dict[str, str]:
    import boto3

    value = boto3.client("secretsmanager").get_secret_value(SecretId=secret_id)["SecretString"]
    return json.loads(value)
