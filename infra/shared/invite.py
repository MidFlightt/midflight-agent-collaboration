"""Operator CLI to create/revoke bounded isolated-demo invite links."""

import argparse
import json
import os
from pathlib import Path
from urllib.parse import urlencode

import httpx


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--admin-token-file", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--revoke", help="Invite ID to revoke, including its issued credentials")
    parser.add_argument("--max-uses", type=int, default=20)
    parser.add_argument("--lifetime-hours", type=int, default=168)
    parser.add_argument("--access-hours", type=int, default=168)
    args = parser.parse_args()
    if not args.url.startswith("https://"):
        parser.error("Use HTTPS")
    if not args.revoke and (not args.output or args.output.exists()):
        parser.error("Create requires a new --output path")
    headers = {"Authorization": "Bearer " + args.admin_token_file.read_text().strip()}
    with httpx.Client(timeout=30, follow_redirects=False) as client:
        if args.revoke:
            response = client.delete(
                args.url.rstrip("/") + "/v1/invites/" + args.revoke, headers=headers
            )
        else:
            response = client.post(
                args.url.rstrip("/") + "/v1/invites",
                headers=headers,
                json=dict(
                    max_uses=args.max_uses,
                    lifetime_hours=args.lifetime_hours,
                    access_hours=args.access_hours,
                ),
            )
        if response.status_code != 200:
            raise SystemExit(f"Invite request failed: HTTP {response.status_code}")
        data = response.json()
    if args.revoke:
        print("Revoked invite and access issued through it. Project data retained.")
    else:
        data["url"] = (
            args.url.rstrip("/")
            + "/invite#"
            + urlencode({"id": data["id"], "secret": data["secret"]})
        )
        with os.fdopen(os.open(args.output, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), "w") as f:
            json.dump(data, f, indent=2)
        print(f"Saved shareable invite to {args.output}. Do not commit it.")


if __name__ == "__main__":
    main()
