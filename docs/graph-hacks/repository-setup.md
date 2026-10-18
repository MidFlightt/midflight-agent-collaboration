# Local mode: MidFlight on one computer

> This guide covers **local mode**: one person, one computer, optionally several agents in
> worktrees. Its service listens only on 127.0.0.1 and refuses other host names, and its
> worktree credentials are copies of one person's local identities. It is **not** a way
> for people on different computers to collaborate: for that, use the team server in the
> root README ("Set up a team" and "Join a team").

Follow the root README for install and `midflight up`. This guide covers the reusable
integration in more detail, not the synthetic four-agent presentation.

## Commands

| Command | What it does |
| --- | --- |
| `midflight up` | Starts FalkorDB (Docker) and the service in the background if needed, then connects the current repository. Safe to rerun |
| `midflight status` | Pass/fail checks for FalkorDB, the service, credentials and plan, each with its fix. `--json` prints raw project context. `doctor` is an alias |
| `midflight worktree NAME [PATH]` | Creates a worktree for one agent, with its credentials and identity |
| `midflight agent` | Starts Codex (or Claude Code with `--client claude`) connected as this checkout's identity |
| `midflight mcp` | The stdio MCP server that clients run |
| `midflight down [--db]` | Stops the background service (and FalkorDB); data is kept |
| `midflight init` / `midflight serve` | The two halves of `up`, for a foreground service or custom setups |

All of them default `--repo` to the Git repository containing the current directory.
The identity defaults to the worktree's (written by `midflight worktree`), or `lead`
in the main checkout. Pass `--identity` to override.

## Service and identities

`midflight serve` (or `up`) creates a private `~/.local/share/midflight/setup.key` and
starts one FalkorDB-backed service. `--home`, `--port`, `--db-port` and `--graph` select a different
local installation. `init --home` must select the same administration-key directory;
`init --url` must point at the same service. Both service and database stay on loopback.

`init --agents backend,frontend,tests` creates a lead plus the named agent identities.
`--repository owner/name` is only a label locally; it defaults to the `origin` remote,
or `local/<folder>`. Names use lowercase letters, digits and hyphens.
Each session uses one identity; tasks refer to the member IDs returned by
`project_context`. The same person can operate several identities. The service stores
token hashes; plaintext tokens stay in `.midflight/private.json` with mode 0600.

The local bootstrap endpoint exists only in `midflight serve`, not the ordinary hosted
entry point. It requires the private setup key. A normal participant token cannot create
projects, and an agent cannot propose or approve plans. The MCP agent adapter doesn't
expose lead tools. REST permissions enforce the boundary even if local configuration
is edited. This is local-machine administration, not a multi-tenant hosting design.

`init` also generates **MIDFLIGHT.md** in the application repository: a human-facing
start guide with exact connection checks, per-identity commands and suggested first
messages. It preserves an existing guide if the repository owner has edited it.

## Normal conversations

In the main checkout, start `claude` (via `.mcp.json`) or `midflight agent`. Describe the actual application and
ask for a proposed plan. Review the requirements, task owners, acceptance criteria and
contract fields before explicitly approving. Approval remains a human instruction to
the lead, not a separate cryptographic proof of human consent.

Start the other identities the same way inside their worktrees. Ask them to implement
their tasks. `project_context` supplies identity, members and the current plan; `get_plan`
lets the lead inspect a draft. The standard claim/check-in/acknowledgement tools do the
coordination. New product directions use `propose_plan` and `approve_plan`; there is no
subscription-specific tool in this adapter.

`midflight agent` passes MCP configuration for that invocation only and leaves existing
client settings and approvals in force by default. `--client claude` uses Claude Code
with `--mcp-config`; arguments after `--` go to the client (for example `-- -m MODEL`). The optional explicit
`--approve-coordination-tools` flag preapproves only context, claim, check-in and
acknowledgement tools in this session; plan writes are excluded. Complete the client's normal sign-in, workspace
trust and tool approval prompts when asked. It doesn't choose a model or disable the
sandbox; pass a model after `--` if your default one isn't available. Its optional headless `--exec` run requests the workspace-write sandbox.
The `-c` override behavior follows [Codex configuration documentation](https://learn.chatgpt.com/docs/config-file/config-advanced).

Other clients run the same stdio adapter: `midflight mcp` inside the repository or
worktree, or the absolute command in `.midflight/mcp-NAME.json`.
Use a client that reads `AGENTS.md`, or install that managed section into the client's
own persistent repository instructions. Merely connecting tools does not force an agent
to call them.

## Parallel Git worktrees

Commit the files `init` added (`AGENTS.md`, `.gitignore`, `.mcp.json`, `MIDFLIGHT.md`),
then create one worktree per agent:

```sh
midflight worktree backend                 # ../<repo>-backend on branch backend-work
midflight worktree frontend ~/work/web --branch web
```

The command refuses to run until those files are committed, so every worktree gets
the instructions. It copies `.midflight/private.json` with mode 0600, records the
identity in `.midflight/identity`, and writes that worktree's client snippet. The
identities still belong to the same shared project; do not rerun `init` in a worktree.

MidFlight doesn't merge branches, grant shared-file ownership or eliminate conflicts.
Normal review and integration testing remain necessary.

## Recovery and troubleshooting

- Start with `midflight status`: it says which part is down and what to run. It does not
  approve plans or claims. No approved plan is normal immediately
  after initialization; ask the lead to propose one.
- Connection refused: run `midflight up`. The service log is `~/.local/share/midflight/serve.log`. A healthy
  HTTP process alone is not proof of a completed review; inspect the claim/job status.
- Setup key missing: use the `--home` used by `serve`. The key must not enter Git or a
  prompt. `init` checks the key and the service before writing anything, so a failed
  attempt leaves the repository untouched. Repeated initialization reuses saved credentials.
- Different setup already registered: rerun with the saved values the error lists. If the
  service never accepted the saved setup, `init` replaces it automatically. Adding agents to
  a registered project, lost-credential recovery and identity migration are not implemented.
- "Credentials rejected" after recloning MidFlight: the Compose project is pinned to
  `midflight-agent-collaboration`, so every clone uses one volume. If you used a clone in
  another folder before this change, set `COMPOSE_PROJECT_NAME=<that folder>` to reach
  its old volume.
- Unknown task/member: inspect `project_context`; plans use full participant IDs, not
  just `backend`. The agent must have an approved task before claiming work.
- Idle agents don't react: ask them to continue/check in. There is no generic client
  interrupt hook or automatic polling loop in this integration.
- MCP tool timed out: don't assume approval. Check the job/claim again; the worker
  persists jobs and retries bounded transport/handler failures across restarts.
- No GitHub App: local claims and graph propagation still work, but GitHub diff
  verification/check publication is unavailable. Run application tests independently.
- FalkorDB missing: startup fails rather than falling back to an empty memory store.
- Restart: stop the one service and start it with the same graph and private home.
  Never start two workers against that graph. Normal Compose shutdown preserves its
  volume; deleting the volume destroys the graph and requires a new installation.

## What is installed

- `AGENTS.md`: one appended, marked section; existing instructions are retained.
- `.mcp.json`: adds a `midflight` server running `midflight mcp`; other servers are kept.
  No paths or tokens, so it is safe to commit.
- `MIDFLIGHT.md`: human-facing start guide with portable commands; existing owner edits
  are preserved.
- `.gitignore`: excludes `.midflight/` before credentials are written.
- `.midflight/private.json`: project URL/ID and separate lead/agent credentials.
- `.midflight/identity`: in worktrees only; the identity `midflight mcp` uses there.
- `.midflight/mcp-NAME.json`: machine-local client snippets with absolute paths and no tokens.

No initial plan, example functions, artificial directives, generated code or global
client configuration is installed. Agent work is normal work in your repository.
