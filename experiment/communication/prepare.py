"""Offline preparation only: never imports a model runner or opens a database."""

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import case
import client

ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(destination, model=client.MODEL, project="pp261018"):
    if not project or not project.isalnum():
        raise ValueError("Use an alphanumeric isolated project ID")
    destination.mkdir(parents=True, exist_ok=False)
    shutil.copytree(
        case.SOURCE, destination / "case", ignore=shutil.ignore_patterns("results", "__pycache__")
    )
    snapshots = destination / "case"
    shutil.copy2(Path(__file__).with_name("chat.py"), snapshots / "overlays/A/tools/chat.py")
    (snapshots / "starter" / "DEPENDENCIES.json").write_text(
        json.dumps(case.DEPENDENCIES, indent=2)
    )
    (snapshots / "starter" / "OWNERS.json").write_text(json.dumps(case.OWNERS, indent=2))
    # Hide old case instructions from future agents: only starter is cloned for them.
    prompts = {}
    for approach in ("N", "A", "B"):
        prompts[approach] = {
            "phases": {
                str(n): {a: case.prompt(approach, a, n, "fresh-run-graph") for a in agents}
                for n, agents in case.PHASES.items()
            },
            "lead": {
                step: case.lead(approach, step, "fresh-run-graph")
                for step in ("plan", "answer", "change")
            },
        }
    (destination / "prompts.json").write_text(json.dumps(prompts, indent=2))
    provenance = destination / "provenance"
    provenance.mkdir()
    # Include only provenance produced on this checkout, never historical pilot outcomes.
    for name, source in {
        "client-discovery.json": "runs/client-preflight/discovery.json",
        "backend-preflight.json": "runs/local-backend/preflight.json",
    }.items():
        path = ROOT / source
        if path.exists():
            shutil.copy2(path, provenance / name)
    # Freeze executable source as well as hashes, so later harness edits remain auditable.
    source_files = [
        ROOT / "experiment/run.py",
        case.SOURCE / "case.py",
        case.SOURCE / "plan.py",
        *sorted(Path(__file__).parent.glob("*.py")),
        *sorted((ROOT / "midflight/communication").glob("*.py")),
    ]
    for source in source_files:
        target = provenance / "source" / source.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    manifest = {
        "status": "prepared-not-run",
        "protocol": "pigeonpost-local-object-v6",
        "source_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "approaches": {"N": "no channel", "A": "team chat", "B": "four-tool MidFlight"},
        "model": model,
        "coding_client": "codex-cli 0.162.1",
        "response_format": "compact-v1: lossless, response-local text sharing",
        "checkpoint_policy": "natural boundaries; reuse updates returned by other tools",
        "reasoning_effort": client.EFFORT,
        "service_tier": "default",
        "max_tool_items_per_call": 50,
        "max_seconds_per_call": 600,
        "cloud_project": project,
        "backend_label": "local authenticated HTTPS; dedicated FalkorDB",
        "endpoint": client.URL,
        "owners": case.OWNERS,
        "runtime_files": {
            str(p.relative_to(ROOT)): digest(p)
            for p in sorted((ROOT / "midflight/communication").glob("*.py"))
        },
        "parallel_agents": 3,
        "max_repair_rounds": 3,
        "steps": case.STEPS,
        "dependencies": case.DEPENDENCIES,
        "harness_files": {
            str(p.relative_to(ROOT)): digest(p)
            for p in [
                ROOT / "experiment/run.py",
                case.SOURCE / "case.py",
                case.SOURCE / "plan.py",
                *sorted(Path(__file__).parent.glob("*.py")),
            ]
        },
        "files": {
            str(p.relative_to(destination)): digest(p)
            for p in sorted(destination.rglob("*"))
            if p.is_file()
        },
    }
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"Prepared {destination}; no agent, database, or benchmark started.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    parser.add_argument(
        "--model", default=client.MODEL, help="Use an exact model ID for scored runs"
    )
    parser.add_argument("--project", default="pp261018")
    args = parser.parse_args()
    prepare(args.destination.resolve(), args.model, args.project)
