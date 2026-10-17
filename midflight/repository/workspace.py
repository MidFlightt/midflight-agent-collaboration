"""Files installed beside the agent instructions: a client config and a human start guide."""

from __future__ import annotations

import json


def install_client_config(repo):
    """A portable `.mcp.json` (Claude Code's project format) safe to commit: no paths or tokens.

    `midflight mcp` finds the repository from its working directory and the identity
    from the worktree, so the same file works in every checkout.
    """
    path = repo / ".mcp.json"
    try:
        data = json.loads(path.read_text()) if path.exists() else {}
    except json.JSONDecodeError:
        raise ValueError(".mcp.json isn't valid JSON; fix it and rerun init") from None
    servers = data.setdefault("mcpServers", {})
    if "midflight" not in servers:
        servers["midflight"] = {"command": "midflight", "args": ["mcp"]}
        path.write_text(json.dumps(data, indent=2) + "\n")


def install_start_guide(repo, config):
    guide = repo / "MIDFLIGHT.md"
    if guide.exists():
        return  # Preserve any guide the repository owner has already edited.
    agents = [name for name in config["identities"] if name != "lead"]
    lines = [
        "# Start the MidFlight coding sessions",
        "",
        f"Service: `{config['url']}`. Project: `{config['repository']}`.",
        "",
        "Run these commands inside this repository. They need the `midflight` command",
        "(`uv tool install`, see MidFlight's README). This file has no secrets or",
        "machine paths, so it's safe to commit.",
        "",
        "## 1. Check everything is running",
        "",
        "```sh",
        "midflight status",
        "```",
        "",
        "If something is down, `midflight up` starts it. Don't delete `.midflight/`:",
        "it holds this repository's credentials.",
        "",
        "## 2. Start the lead in this checkout",
        "",
        "- **Claude Code:** run `claude` here. `.mcp.json` connects it; approve the",
        "  `midflight` server when asked.",
        "- **Codex:** `midflight agent` (add `-- -m MODEL` to pass flags to Codex).",
        "",
        "Ask: **Show me the current plan and task assignments.** If no plan exists, describe",
        "your application and ask for a proposed plan. Review it before approving it.",
        "",
        "## 3. Start each agent in its own worktree",
        "",
        "Commit the MidFlight files once, so worktrees get them:",
        "",
        "```sh",
        "git add AGENTS.md .gitignore .mcp.json MIDFLIGHT.md && git commit -m 'Connect MidFlight'",
        "```",
        "",
    ]
    for name in agents:
        lines += [
            f"### {name}",
            "",
            "```sh",
            f"midflight worktree {name}",
            f"cd ../{repo.name}-{name} && midflight agent    # or: claude",
            "```",
            "",
        ]
    lines += [
        "Ask each agent: **Show my assigned task and its current status.** Then ask it to",
        "implement or continue that task. It should check in and obtain claim approval",
        "before changing code. Run application tests independently.",
        "",
        "## 4. Change direction",
        "",
        "Give the product change to the lead. Review and approve its proposed plan update.",
        "Working agents discover relevant directives at their own checkpoints. To resume",
        "an idle agent, ask it to continue/check in. There is no automatic interruption.",
        "",
        "## Stopping",
        "",
        "`midflight down` stops the service; `midflight down --db` also stops FalkorDB.",
        "Your plan, claims and directives stay in the persisted graph. Keep",
        "`.midflight/private.json` private; it must never be committed or pasted into chat.",
        "",
    ]
    guide.write_text("\n".join(lines))
