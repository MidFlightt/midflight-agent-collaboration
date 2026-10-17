# Four-agent local acceptance demo

For the live presentation, use **Persistent interactive coding terminals** below.
The optional dashboard mode described first streams agent output for inspection.

Run four real Codex CLI agents in one browser split screen. Each has an independent
Git workspace and MidFlight MCP identity. One local service coordinates them through
FalkorDB and its recovery worker. Model calls use the local Codex sign-in and consume
that account's usage. Check `codex login status` before starting.

```sh
uv sync --locked --extra falkordb
docker compose -f compose.graph-hacks.yml up -d
uv run --extra falkordb python -m midflight.theater.app --port 8895 --api-port 8896
```

Open `http://127.0.0.1:8895`. Click **Start agents**, wait for the initial build, then
click **Introduce pricing change**. The lead approves one change; the second round's
agents get its content only through MidFlight check-in. Pricing and Checkout should
receive directives; Notifications should keep its implementation. Reporting's indirect
notification remains pending dependency-graph integration and is not counted as passed.

The panes stream actual agent messages, MCP tool calls and command results. An agent
exit alone does not establish acceptance: **Run evidence** checks claims, scoped
directives and a separate commerce integration script against the files produced.
Each process has a ten-minute deadline. Ctrl+C stops this run's service and agents;
the database volume and run evidence are retained.

Every launch creates a fresh synthetic project/graph and private workspace directory
under `~/.local/share/midflight-demo/`. Logs and `report.json` stay there. Reports record
the tested Git SHA and whether the checkout was modified. For a merged-PR acceptance
run, check out the exact merged SHA in a clean worktree and start the harness there.
Use **New run** to repeat without overwriting earlier artifacts. Use a new run for every tested commit. A dirty run is development evidence only.

Only this run's local MCP tools (`check_in`, `submit_claim`, `acknowledge_directive`)
are preapproved for its agent processes. Global Codex configuration is not loaded or
modified; agents retain the workspace-write sandbox. Token values are passed only to
the corresponding local MCP process and are not put in the browser state/report.
The dashboard/API bind to loopback. Keep the demo local.

This is a manual acceptance harness; ordinary CI remains deterministic and does not
launch paid model sessions. PRs should link the run's commit and acceptance report.
No automatic merge or production deployment is performed.

## Persistent interactive coding terminals

For genuine interactive Codex interfaces that keep the same conversation between
stages, use the terminal mode:

```sh
brew install tmux                  # macOS; use your package manager on Linux
uv sync --locked --extra falkordb --extra demo
uv run --extra falkordb --extra demo python -m midflight.theater.interactive
```

Open `http://127.0.0.1:8897`. The four panes are actual interactive Codex TUIs inside
PTYs owned by tmux, displayed through a locally served terminal emulator. Click a pane
to select it and type normally. On first launch, approve access to each newly generated
synthetic workspace. The default layout is Pricing/Checkout above Reporting/Notifications.
`Ctrl-b` then an arrow changes pane; `Ctrl-b` then `z` zooms the selected pane.

The initial prompt starts all agents. Once their initial work is complete, **Introduce
plan change** approves the shared change and sends a neutral checkpoint request to those
same four TUIs. The actual change is obtained through MidFlight MCP. Model processes
remain alive at their prompts after both stages, ready for further interaction. Browser
refresh/disconnection detaches the view without restarting the agents. Stopping the
harness ends its tmux session and local API; this mode has no unattended loop sending
repeated prompts and no ten-minute per-turn cutoff.

Native terminal attachment is also possible: `tmux attach -t <session>`. The exact session,
pane IDs, workspace and tested commit are in the run's `interactive.json`. The view is
only a terminal attachment; neither this mode nor the dashboard imitates model output.

Each interactive agent has a private Codex profile under its run directory, with a
symlink to the existing local `~/.codex/auth.json` for sign-in. Global configuration is
not edited, and credentials are not copied into the repository. Each process is configured
with its own local demo MCP server, workspace-write sandbox and per-tool approval.
Other global MCP configuration is not loaded into these profiles. No third-party CDN
receives terminal contents: xterm.js assets and license notices are vendored locally.

The terminal bridge binds to loopback, checks allowed hosts and WebSocket Origin, and
requires a per-run key for terminal/control access. Only trusted local users should have
access to its URL: typing into a pane controls a real coding agent. **Test evidence**
checks stored claims and the independent integration test rather than treating a still
running TUI process as unfinished work. Downstream graph propagation remains pending.
