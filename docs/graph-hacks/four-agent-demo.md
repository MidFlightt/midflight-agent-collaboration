# Four-agent local acceptance demo

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
