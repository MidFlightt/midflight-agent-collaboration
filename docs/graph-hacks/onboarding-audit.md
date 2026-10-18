# Onboarding audit (TEAM-04)

Where installing and connecting MidFlight to a new repository can be simpler. Method:
a code and docs review of PR #7, plus one fresh run of its README on a clean machine
checkout. This is not a multi-agent end-to-end test; coordination correctness is
TEAM-07.

**Tested:** `GH-07-repository-onboarding` at `51fe076`, macOS 26.6.2 arm64, Docker 29.5.2
(Compose v5.5.1), uv 0.11.28, Codex CLI 0.145.0, Claude Code 2.1.296. Fresh clone in
`fresh/midflight`, new empty app repo `fresh/try-app`, default ports 8000/6379 free.

> **Correction.** This audit and the first TEAM-04 changes covered one person running
> several agents on one computer. Local mode's localhost service and copied worktree
> credentials do not give people on different computers a way to collaborate. The team
> path is the hosted connector on FalkorDB (`midflight host`): Sign in with GitHub, join
> codes, per-person tokens and lead-only tools. See the root README, journeys A and B.

## Status after the TEAM-04 changes

Built on this branch: fixes 1, 2, 4, 5, 6, 7, 8 (`midflight status`; `/healthz` is unchanged,
and `status` checks FalkorDB directly), 9, 11, 12 and 13, plus `midflight up` / `down`
(fix 3). FalkorDB stays an optional extra: the install command names it, so the AWS
Lambda bundle doesn't grow. Open: 10 (adding agents later) and 14 (single-server lock).

Re-run of the new flow, via `uv tool install` from this branch into a fresh app repo with
FalkorDB and the service stopped:
- `midflight up --agents backend,frontend` started FalkorDB and the service and connected
  the repo in 12.7 s.
- `midflight worktree backend` refused until the files were committed, then created the
  worktree.
- The committed `.mcp.json` (`midflight mcp`) served backend's tools in the worktree and the
  lead's tools in the main checkout. Claude Code listed it as pending approval.
- `midflight down --db` then `midflight up` kept the credentials, and `status` passed in the
  worktree.

## Baseline: what a new user does today

Before the first agent can call `project_context`:

| Measure | Today |
| --- | --- |
| Commands | 8: clone, `cd`, `uv sync …`, `docker compose … up -d`, `serve`, `init`, `doctor`, `agent` |
| Terminals | 2 before any agent (one is held by `serve`), then one per agent |
| Flags to type | 14, including `--extra falkordb` twice and the absolute `--repo` path three times |
| Per extra parallel agent | about 4 manual steps: commit `AGENTS.md`, `git worktree add`, copy `private.json`, `chmod` |
| Concepts to learn | uv extras, Compose file name, graph name, setup key and `--home`, `owner/name` identifier, lead vs. agent, identities, worktrees, `private.json`, MCP snippet, approval flag |
| Wall-clock time | under 30 s of machine time (clone 1 s, `uv sync` 1.4 s with a warm cache, `compose up` 19.5 s, `serve` ready about 3 s, `init` 1 s) |

The time is fine. **The friction is how much a user has to know, and the error
messages when anything is off.**

## What happened on the run

| Step | Result |
| --- | --- |
| `uv sync --python 3.12 --locked --extra falkordb` | OK |
| `docker compose -f compose.graph-hacks.yml up -d` | OK, but it returns while the container is still `health: starting` |
| `init` before `serve` (an easy ordering mistake) | `MidFlight setup failed: FileNotFoundError. [Errno 2] … setup.key`. **It had already written `.midflight/private.json` and `.gitignore`.** |
| Retry with a different agent list | `Existing setup differs … it was not overwritten.` The agent list is now locked, although the server never registered anything |
| Retry with the original arguments | OK, about 1 s |
| `doctor` (lead, backend) | OK; prints raw JSON |
| `midflight` from inside the app repo | `command not found`. Every command has to run from the MidFlight checkout |
| Codex: `midflight agent … --exec` | Blocked by this machine's Codex account (the configured model isn't available on a ChatGPT login). `agent` has no way to pass `-m` or other Codex flags, so the only workaround is editing global Codex config |
| Claude Code with the generated snippet | Blocked by an expired headless login on this machine (not a MidFlight problem) |
| Generated snippet through a plain MCP stdio client | **OK.** `mcp-frontend.json`: 5 agent tools, `project_context` returns the frontend identity. `mcp-lead.json`: adds `propose_plan` and `approve_plan`. The snippet is already in Claude Code's `--mcp-config` format |

Error messages for common mistakes:

| Mistake | What the user sees |
| --- | --- |
| Wrong or missing `--home` | `FileNotFoundError … nohome/setup.key` |
| Repo isn't a Git repo | `CalledProcessError: Command '['git', '-C', …, 'rev-parse', '--show-toplevel']' returned non-zero exit status 128.` |
| Subdirectory passed as `--repo` | `Pass the Git repository root, not a subdirectory` (good) |
| `--repository app2` with no slash | Pydantic `ValidationError … String should match pattern '^[\w.-]+/[\w.-]+$'` |
| `doctor --identity tests` (not created) | `KeyError. 'tests'` |
| `doctor` after a partial `init` | Uncaught traceback ending `NotSignedIn: Invalid or revoked participant token` |
| `serve` while FalkorDB is down | Long `redis.exceptions.ConnectionError … Connection refused` traceback |
| Second `serve` on a busy port | App startup runs against the shared graph, then `[Errno 48] address already in use` |

## Findings, ranked

Impact means how often a new user hits it and how stuck they get. Effort is a rough
size for one person.

| # | Problem | Evidence | Proposed fix | Impact | Effort | Files |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Errors show exception class names and tracebacks, with no next step | See the error table above | Map each failure to one line with the fix: "Start `midflight serve` first", "Not a Git repo: run `git init`", "Unknown identity; choose lead, backend, frontend", "FalkorDB isn't reachable on 6379: run `docker compose … up -d --wait`". Catch `NotSignedIn` | High | S | `repository/cli.py:286-298`, `repository/cli.py` `serve` |
| 2 | `init` writes credentials before it knows the service accepts them, so one failed attempt locks the identity list and repository | `cli.py:101-103` writes `private.json` before the HTTP call at `:111` | Check the setup key and `/healthz` before writing files. If the server has no such project, let `init` replace the unregistered local config. Say which field differs | High | S | `repository/cli.py` `initialize` |
| 3 | FalkorDB is a separate step, an optional extra, and has no health wait | README needs `--extra falkordb` twice; `compose up` returns before healthy | Make `falkordb` and `redis` default dependencies. `serve` checks the DB, and if it's unreachable runs the bundled Compose file with `--wait` (or prints the exact command) | High | M | `pyproject.toml`, `repository/cli.py` `serve`, `compose.graph-hacks.yml` |
| 4 | The database volume is named after the checkout folder, so re-cloning or renaming the folder starts an empty graph and existing `private.json` tokens become "revoked" | Volume is `midflight_graph-hacks-data` here; a teammate's clone gets `midflight-agent-collaboration_graph-hacks-data` | Add a top-level `name: midflight` to the Compose file (or a fixed volume `name:`) | High (silent data split) | XS | `compose.graph-hacks.yml` |
| 5 | Every command runs from the MidFlight checkout with absolute `--repo` paths | `command not found: midflight` in the app repo; snippets and `MIDFLIGHT.md` embed `…/midflight/.venv/bin/python3` | Document `uv tool install "midflight @ git+…"` so `midflight` is on PATH. `--repo` defaults to the current directory; snippets and the guide call `midflight` | High | M | `repository/cli.py`, `repository/workspace.py`, README |
| 6 | Claude Code (and other clients) have no documented path, and `agent` can't pass flags through to Codex | Codex blocked with no `-m` passthrough; the snippet already works as `claude --mcp-config` | `midflight agent --client claude` runs `claude --mcp-config .midflight/mcp-NAME.json`. Pass anything after `--` to the client. Document both | Med-High | S | `repository/cli.py` `codex_command`/`agent`, README |
| 7 | Parallel agents need 4 manual worktree steps each | `repository-setup.md` "Parallel Git worktrees" | `midflight worktree NAME [PATH]`: checks `AGENTS.md` is committed, runs `git worktree add`, copies `private.json` with mode 0600, prints the launch command | Med-High | S | `repository/cli.py` |
| 8 | `doctor` and `/healthz` don't actually diagnose anything | `/healthz` always returns `{"status":"ok"}` (`api/app.py:174-176`); `doctor` dumps JSON | `doctor` prints pass/fail for: service reachable, DB reachable, token valid, project found, plan present, with the fix on each failure. `/healthz` pings the store | Med | S | `repository/cli.py`, `api/app.py` |
| 9 | `--repository owner/name` is required but unused locally | Pattern error for `app2` | Default it from `git remote get-url origin`, falling back to `local/<folder>` | Med | XS | `repository/cli.py` |
| 10 | Can't add an agent after `init` | `cli.py:74-82` requires identical names | `init --agents` adds new identities to an existing project (a new server route to add participants) | Med | M | `repository/cli.py`, `repository/server.py` |
| 11 | `MIDFLIGHT.md` assumes VS Code and Codex, and holds machine-local absolute paths in the repo root. Users are told to commit `AGENTS.md`, so `git add .` would commit it too | Generated file, step 1 "In VS Code…" | Write it to `.midflight/START.md` (ignored), or generate portable `midflight …` commands and cover the Claude Code path | Med | XS | `repository/workspace.py` |
| 12 | The README says to clone `main`, but the CLI only exists on the PR branch | `main`'s `pyproject.toml` has no `midflight` script | Merge #7, or have the README name the branch until then | Med (now) | XS | README |
| 13 | MCP server name differs by client: `midflight` in snippets, `midflight_repository` in the Codex launcher | `cli.py` snippet vs. `codex_command` | Use `midflight` everywhere, which `AGENTS.md` already names | Low | XS | `repository/cli.py` |
| 14 | Nothing prevents two servers or workers on one graph, though the docs say never do it | A second `serve` ran app startup before the port error | Take a graph-level lock at startup (a Redis key with a TTL), and refuse to start with a clear message | Low (onboarding), Med (safety) | M | `repository/cli.py` `serve` |

## What onboarding could look like after fixes 1–9

```sh
uv tool install "midflight @ git+https://github.com/MidFlightt/midflight-agent-collaboration"
midflight serve                      # starts FalkorDB if needed, waits until healthy
cd ~/code/your-app
midflight init --agents backend,frontend
midflight agent lead                 # or: midflight agent lead --client claude
midflight worktree backend && midflight agent backend --repo ../your-app-backend
```

That's 5 commands instead of 8. There are no `--extra`, `--repository` or absolute
`--repo` flags, no manual worktree setup, and every failure prints its fix.

## Suggested order

1. **Quick wins (XS–S, under a day together):** 1, 2, 4, 9, 11, 12, 13.
2. **Biggest simplification (S–M):** 3, 5, 6, 7, 8.
3. **Later:** 10 and 14.

## Not covered

- A real coding agent calling the tools. Both clients were blocked by this machine's
  account and login state; the MCP adapter itself was verified with a plain stdio
  client.
- Approval prompts in interactive sessions, and whether agents follow the installed
  `AGENTS.md`.
- A cold-cache install (no uv cache, no FalkorDB image), Linux, and Windows.
- Another person following the docs without help (TEAM-04 checklist).

## Reproduce

```sh
git clone https://github.com/MidFlightt/midflight-agent-collaboration.git midflight
cd midflight && git checkout 51fe076
uv sync --python 3.12 --locked --extra falkordb
docker compose -f compose.graph-hacks.yml up -d
mkdir ../try-app && git -C ../try-app init && git -C ../try-app commit --allow-empty -m init
uv run midflight init --repo "$PWD/../try-app" --repository local/try-app --agents backend,frontend   # before serve: expect error 1 and 2
uv run --extra falkordb midflight serve    # separate terminal
uv run midflight init --repo "$PWD/../try-app" --repository local/try-app --agents backend,frontend
uv run midflight doctor --repo "$PWD/../try-app" --identity lead
```
