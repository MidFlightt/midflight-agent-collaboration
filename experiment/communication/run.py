"""Explicitly authorized single pilot; never automatically starts a campaign."""

import argparse
import json
import re
import sys
import time
from pathlib import Path

import case
import codex_driver
import prepare
import report

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("run")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--credentials", type=Path)
    parser.add_argument("--resume-run", type=Path)
    args = parser.parse_args()
    if not args.execute:
        parser.error("Preparation only; --execute is required to run.")
    if not re.fullmatch("[NAB][A-Za-z0-9_-]+", args.run):
        parser.error("Use an N/A/B run ID")
    bundle = args.bundle.resolve()
    manifest = json.loads((bundle / "manifest.json").read_text())
    for source, entries in [
        (bundle, manifest["files"]),
        (ROOT, manifest["harness_files"]),
        (ROOT, manifest["runtime_files"]),
    ]:
        for name, expected in entries.items():
            if prepare.digest(source / name) != expected:
                parser.error(f"Frozen file changed: {name}; prepare a new bundle")
    from experiment import run as legacy

    legacy.RUNS = bundle / "runs"
    legacy.MAX_FIX_ROUNDS = manifest["max_repair_rounds"]
    trial = legacy.Trial("pigeonpost", args.run)
    trial.case_dir = bundle / "case"
    trial.case = case
    resuming = args.resume_run is not None
    if resuming:
        trial.root = args.resume_run.resolve()
        previous = json.loads((trial.root / "execution.json").read_text())
        if not str(previous.get("failure", "")).startswith("JSONDecodeError:"):
            parser.error("Resume is restricted to the verified atomic-state harness defect")
        if trial.state().get("pending"):
            parser.error("Uncertain pending turns; refuse replay")
        (trial.root / "execution-before-harness-resume.json").write_text(
            json.dumps(previous, indent=2)
        )
    elif trial.root.exists():
        parser.error("Run exists; preserved. Use a fresh ID, no automatic replay.")
    credentials = args.credentials.resolve() if args.credentials else None
    if trial.with_midflight:
        if credentials is None:
            parser.error("B requires isolated cloud credentials")
        config = json.loads((credentials / "config.json").read_text())
        if set(config["projects"]) != {manifest["cloud_project"]}:
            parser.error("Credentials must belong only to the isolated pilot project")
        for agent in case.DEPENDENCIES:
            if not (credentials / (agent + ".token")).is_file():
                parser.error(f"Missing credential: {agent}")
    prompts = json.loads((bundle / "prompts.json").read_text())
    case.prompt = lambda approach, agent, phase, project: prompts[approach]["phases"][str(phase)][
        agent
    ]
    case.lead = lambda approach, step, project: prompts[approach]["lead"][step]
    if not resuming:
        legacy.setup(trial, manifest["cloud_project"] if trial.with_midflight else None)
    codex_driver.install(legacy, manifest, credentials)
    legacy.record = lambda trial: report.summarize(trial.root)
    started = time.time()
    status = "interrupted"
    failure = None
    try:
        legacy.auto(trial, manifest["cloud_project"])
        status = "completed"
    except BaseException as error:
        failure = f"{type(error).__name__}: {error}"
        raise
    finally:
        (trial.root / "execution.json").write_text(
            json.dumps(
                {
                    "started_at_unix": started,
                    "finished_at_unix": time.time(),
                    "wall_seconds": time.time() - started,
                    "status": status,
                    "failure": failure,
                    "resumed_after_harness_defect": resuming,
                    "model": manifest["model"],
                    "reasoning_effort": manifest["reasoning_effort"],
                    "runtime_commit": manifest["source_commit"],
                    "cloud_project": manifest["cloud_project"] if trial.with_midflight else None,
                    "validated_by": "operator harness; actual combined modules",
                },
                indent=2,
            )
        )
        report.summarize(trial.root)


if __name__ == "__main__":
    main()
