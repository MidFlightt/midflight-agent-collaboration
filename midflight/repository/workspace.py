"""Human-facing start instructions installed beside the agent instructions."""

from __future__ import annotations

import shlex
import sys


def install_start_guide(repo, config):
    guide = repo / "MIDFLIGHT.md"
    if guide.exists():
        return  # Preserve any guide the repository owner has already edited.
    prefix = [sys.executable, "-m", "midflight.repository.cli"]

    def command(kind, identity):
        return shlex.join([*prefix, kind, "--repo", str(repo), "--identity", identity])

    lines = [
        "# Start the MidFlight coding sessions",
        "",
        "This setup runs Codex CLI inside VS Code's integrated terminal. It uses your",
        "existing Codex sign-in. No long coordination prompt is needed: AGENTS.md and",
        "the connected tools provide those instructions.",
        "",
        f"Service: `{config['url']}`. Project: `{config['repository']}`.",
        "",
        "## 1. Open a terminal",
        "",
        "In VS Code, choose **Terminal → New Terminal**. If the workspace is in Restricted",
        "Mode, review the folder and use VS Code's workspace trust controls before running",
        "coding agents. Complete normal Codex sign-in and tool approval prompts when asked.",
        "",
        "## 2. Check the connection",
        "",
        "```sh",
        command("doctor", "lead"),
        "```",
        "",
        "This should show your project, identity and current plan. If connection is refused,",
        "the MidFlight service must be started with its original graph and private home;",
        "see the service checkout's README. Do not reinitialize or delete credentials.",
        "",
        "## 3. Start the lead",
        "",
        "```sh",
        command("agent", "lead"),
        "```",
        "",
        "Ask: **Show me the current plan and task assignments.** If no plan exists, describe",
        "your application and ask for a proposed plan. Review it before approving it.",
        "",
        "## 4. Start the other agents",
        "",
        "Open a separate terminal for each identity you need. For simultaneous file edits,",
        "use separate Git worktrees as described in the service's repository setup guide.",
        "",
    ]
    for name in config["identities"]:
        if name != "lead":
            lines += [f"### {name}", "", "```sh", command("agent", name), "```", ""]
    lines += [
        "Ask each agent: **Show my assigned task and its current status.** Then ask it to",
        "implement or continue that task. It should check in and obtain claim approval",
        "before changing code. Run application tests independently.",
        "",
        "## 5. Change direction",
        "",
        "Give the product change to the lead. Review and approve its proposed plan update.",
        "Working agents discover relevant directives at their own checkpoints. To resume",
        "an idle agent, ask it to continue/check in. There is no automatic interruption.",
        "",
        "## Stopping",
        "",
        "Exit a coding session normally when finished. Your plan, claims and directives",
        "remain in the service's persisted FalkorDB graph. Keep `.midflight/private.json`",
        "private and retain it to reconnect; it must never be committed or pasted into chat.",
        "",
    ]
    guide.write_text("\n".join(lines))
