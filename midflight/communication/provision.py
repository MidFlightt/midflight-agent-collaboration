"""Create an operator config and individual bearer credentials without printing secrets."""

import argparse
import hashlib
import json
import os
import secrets
from pathlib import Path

from .cloud import validate_config


def provision(project, agents, owners, output):
    output = Path(output)
    tokens = {agent: secrets.token_urlsafe(32) for agent in agents}
    config = {
        "projects": {project: {"agents": agents, "owners": owners}},
        "credentials": {
            hashlib.sha256(token.encode()).hexdigest(): {"project": project, "agent": agent}
            for agent, token in tokens.items()
        },
    }
    validate_config(config)
    # Never overwrite existing credentials or reset an existing team.
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    for agent, token in tokens.items():
        path = output / (agent + ".token")
        with open(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as file:
            file.write(token + "\n")
    with open(
        os.open(output / "config.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w"
    ) as file:
        json.dump(config, file, indent=2)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--output", required=True, help="Private new directory, outside Git")
    parser.add_argument(
        "--roster",
        required=True,
        help='JSON file: {"agents":{"name":["topic"]},"owners":{"topic":"name"}}',
    )
    args = parser.parse_args()
    roster = json.loads(Path(args.roster).read_text())
    output = provision(args.project, roster["agents"], roster.get("owners", {}), args.output)
    print(f"Created config and individual token files in {output}; distribute tokens privately.")


if __name__ == "__main__":
    main()
