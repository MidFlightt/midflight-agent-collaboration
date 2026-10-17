"""Run several trials one after another, unattended, and record each one.

Each trial is `<case> <run>` as in run.py. Run B trials get their own Midflight on this
machine (local_midflight.py), started fresh for the trial and stopped after it, with the
reviewer named in the trial (`scripted`, `claude`, or `none`). The lead's part is scripted:

- HireBot Pro, run B: after phase 2 the local lead resolves every waiting escalation with
  the case's fixed decision, and each agent whose claim it sent back is told so. Up to
  three rounds, since a revision can raise a new one.
- HireBot Pro, run A: if anyone raised cancellations in the team chat, the lead posts the
  fixed decision there once and bookings and reports are told to read it, as in run A1.
- HireBot Pro, run N: nobody can ask the lead.
- PigeonPost and Tabby script their own lead (`run.py <case> <run> auto`).

When the Claude plan's usage limit is reached, the step waits and is run again; run.py
skips agents that already finished. Progress goes to stdout.

    python experiment/matrix.py hirebot-pro:B7:scripted pigeonpost:B3:claude pigeonpost:N2
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RUNS = HERE.parents[1] / "experiment-runs"
PY = sys.executable
LIMIT_WAIT = 20 * 60  # seconds to wait after the usage limit, before trying again
LIMIT_MARKS = ("USAGE LIMIT", "UsageLimit", "hit your session limit")
DECIDED = (
    "The lead decided the escalation. Check in with Midflight, then update your part as "
    "needed, commit, and finish with a two-line summary."
)
ANSWERED_IN_CHAT = (
    "The lead answered in the team chat. Read it, update your part as needed, commit, and "
    "finish with a two-line summary."
)


def log(text: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {text}", flush=True)


def step(env: dict[str, str], *args: str, retry: bool = True) -> str:
    """One run.py or local_midflight.py command; waits out the usage limit and retries."""
    while True:
        done = subprocess.run(
            [PY, *args], cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8"
        )
        out = done.stdout + done.stderr
        tail = out.strip().splitlines()[-3:] if out.strip() else []
        log(f"{' '.join(a for a in args[1:4])}: exit {done.returncode} | {' / '.join(tail)[:300]}")
        if done.returncode == 0:
            return out
        if retry and any(mark in out for mark in LIMIT_MARKS):
            log(f"usage limit: waiting {LIMIT_WAIT // 60} minutes")
            time.sleep(LIMIT_WAIT)
            continue
        raise RuntimeError(f"{args} failed:\n{out[-2000:]}")


def start_midflight(case: str, reviewer: str, env: dict[str, str]) -> tuple[subprocess.Popen, str]:
    server_env = env | {
        "MIDFLIGHT_LOCAL_CASE": "hirebot" if case == "hirebot-pro" else case,
        "MIDFLIGHT_LOCAL_REVIEWER": reviewer,
    }
    proc = subprocess.Popen(
        [PY, "experiment/local_midflight.py", "serve"],
        cwd=ROOT, env=server_env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )  # fmt: skip
    assert proc.stdout
    for line in proc.stdout:
        found = re.search(r"PROJECT (\S+)", line)
        if found:
            # Keep reading in the background so the pipe never fills up.
            import threading

            threading.Thread(target=lambda: [None for _ in proc.stdout], daemon=True).start()
            return proc, found.group(1)
    raise RuntimeError("local Midflight stopped before printing its project")


def lead(env: dict[str, str], action: str) -> str:
    return step(env, "experiment/local_midflight.py", "lead", action, retry=False)


def agents_sent_back(rule_output: str, status: str) -> list[str]:
    """The agents whose claims the lead's decisions updated, from the claim ids named."""
    claims = set(re.findall(r"\bC-\d+\b", " ".join(re.findall(r"Claims? ([^.]*) w", rule_output))))
    agents = []
    for task, claim in re.findall(r"^- (T\d) [^:]*: claim (C-\d+)", status, re.M):
        if claim in claims:
            agents.append(task.lower())
    return agents


def hirebot(run: str, env: dict[str, str], project: str | None) -> list[str]:
    notes = []
    case = "hirebot-pro"
    step(env, "experiment/run.py", case, run, "setup", *([project] if project else []))
    step(env, "experiment/run.py", case, run, "phase", "1")
    if run.startswith("B"):
        lead(env, "plan")
    step(env, "experiment/run.py", case, run, "phase", "2")
    if run.startswith("B"):
        for round_ in range(1, 4):
            status = lead(env, "status")
            if "Open escalations: 0" in status:
                break
            ruled = lead(env, "rule")
            told = agents_sent_back(ruled, status)
            notes.append(f"Lead round {round_}: {ruled.strip()[:600]} Told: {', '.join(told)}.")
            for agent in told:
                step(env, "experiment/run.py", case, run, "say", agent, DECIDED)
        notes.append("Final project status: " + lead(env, "status").strip()[:3000])
    elif run.startswith("A"):
        chat = (RUNS / case / run / "TEAM_CHAT.md").read_text(encoding="utf-8")
        asked = [line for line in chat.splitlines() if re.search(r"cancel", line, re.I)]
        if asked:
            sys.path.insert(0, str(HERE / "cases" / case))
            import case as hirebot_case  # type: ignore[import-not-found]

            with (RUNS / case / run / "TEAM_CHAT.md").open("a", encoding="utf-8") as chat_file:
                chat_file.write(f"Lead: {hirebot_case.LEAD_DECISION}\n")
            notes.append(f"The lead answered once in the chat, after: {asked[0][:300]}")
            for agent in ("t3", "t4"):
                step(env, "experiment/run.py", case, run, "say", agent, ANSWERED_IN_CHAT)
        else:
            notes.append("Nobody raised cancellations in the chat, so the lead said nothing.")
    step(env, "experiment/run.py", case, run, "merge")
    step(env, "experiment/run.py", case, run, "repair", retry=True)
    return notes


def scripted(case: str, run: str, env: dict[str, str], project: str | None) -> list[str]:
    """PigeonPost and Tabby script every step, the lead included."""
    step(env, "experiment/run.py", case, run, "auto", *([project] if project else []))
    return []


def trial(spec: str) -> None:
    case, run, *rest = spec.split(":")
    reviewer = rest[0] if rest else "none"
    root = RUNS / case / run
    if (root / "state.json").exists() and json.loads((root / "state.json").read_text()).get(
        "matrix_done"
    ):
        log(f"{case} {run}: already done")
        return
    env = os.environ | {"MIDFLIGHT_MCP_CONFIG": str(HERE / "midflight-local.mcp.json")}
    env.pop("VIRTUAL_ENV", None)
    server, project = None, None
    sha = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True
    ).stdout.strip()
    started = time.time()
    log(f"=== {case} {run} (reviewer {reviewer}, Midflight {sha})")
    try:
        if run.startswith("B"):
            server, project = start_midflight(case, reviewer, env)
            env["MIDFLIGHT_EXPERIMENT_PROJECT"] = project
            log(f"local Midflight project {project}")
        if case == "hirebot-pro":
            notes = hirebot(run, env, project)
        else:
            notes = scripted(case, run, env, project)
        if server is not None:
            notes.append(f"Reviewer: {lead(env, 'reviewer').strip()}")
    finally:
        if server is not None:
            server.terminate()
    state_file = root / "state.json"
    state = json.loads(state_file.read_text(encoding="utf-8"))
    head = (
        f"Run unattended by experiment/matrix.py on {datetime.now(UTC):%B %d, %Y}, Midflight at "
        f"{sha}, the `sonnet` alias of that day. "
    )
    if run.startswith("B"):
        head += (
            "Run against a Midflight on the same machine (experiment/local_midflight.py): "
            f"everything in memory, one person signed in who leads and owns every task; "
            f"reviewer: {reviewer}."
        )
    state["notes"] = [head, *notes, f"Wall time {round((time.time() - started) / 60)} minutes."]
    state["matrix_done"] = True
    state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")
    step(env, "experiment/run.py", case, run, "record", retry=False)
    log(f"=== {case} {run} recorded")


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    for spec in sys.argv[1:]:
        try:
            trial(spec)
        except Exception as error:  # one broken trial doesn't stop the rest
            log(f"!!! {spec} failed: {type(error).__name__}: {str(error)[:1500]}")


if __name__ == "__main__":
    main()
