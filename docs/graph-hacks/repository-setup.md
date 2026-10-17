# Use MidFlight on an existing repository

Follow the root README for install, database startup and `midflight serve`. This guide
covers the reusable integration, not the synthetic four-agent presentation.

## Service and identities

`midflight serve` creates a private `~/.local/share/midflight/setup.key` and starts one
FalkorDB-backed service. `--home`, `--port`, `--db-port` and `--graph` select a different
local installation. `init --home` must select the same administration-key directory;
`init --url` must point at the same service. Both service and database stay on loopback.

`init --repo PATH --repository owner/name --agents backend,frontend,tests` creates a lead
plus the named agent identities. Names use lowercase letters, digits and hyphens.
Each session uses one identity; tasks refer to the member IDs returned by
`project_context`. The same person can operate several identities. The service stores
token hashes; plaintext tokens stay in `.midflight/private.json` with mode 0600.

The local bootstrap endpoint exists only in `midflight serve`, not the ordinary hosted
entry point. It requires the private setup key. A normal participant token cannot create
projects, and an agent cannot propose or approve plans. The MCP agent adapter doesn't
expose lead tools. REST permissions enforce the boundary even if local configuration
is edited. This is local-machine administration, not a multi-tenant hosting design.

## Normal conversations

Start `midflight agent --repo PATH --identity lead`. Describe the actual application and
ask for a proposed plan. Review the requirements, task owners, acceptance criteria and
contract fields before explicitly approving. Approval remains a human instruction to
the lead, not a separate cryptographic proof of human consent.

Start the other identities with the same command and their names. Ask them to implement
their tasks. `project_context` supplies identity, members and the current plan; `get_plan`
lets the lead inspect a draft. The standard claim/check-in/acknowledgement tools do the
coordination. New product directions use `propose_plan` and `approve_plan`; there is no
subscription-specific tool in this adapter.

The launcher passes MCP configuration for that invocation only and leaves existing
Codex settings and approvals in force by default. The optional explicit
`--approve-coordination-tools` flag preapproves only context, claim, check-in and
acknowledgement tools in this session; plan writes are excluded. Complete the client's normal sign-in, workspace
trust and tool approval prompts when asked. It doesn't choose a model or disable the
sandbox. Its optional headless `--exec` run requests the workspace-write sandbox.
The `-c` override behavior follows [Codex configuration documentation](https://learn.chatgpt.com/docs/config-file/config-advanced).

Other clients can start the same stdio adapter from the generated MCP snippet. Their
configuration wrappers differ; the common data are its executable and argument list.
Use a client that reads `AGENTS.md`, or install that managed section into the client's
own persistent repository instructions. Merely connecting tools does not force an agent
to call them.

## Parallel Git worktrees

Initialize the main checkout first. For each simultaneous coding session, create a
separate branch/worktree from an existing commit, for example:

```sh
git -C /path/to/repo worktree add -b backend-work /path/to/backend-work
```

The instruction section must be present in each worktree: commit the non-secret
`AGENTS.md`/`.gitignore` changes before creating them, or copy those two files carefully.
Copy `.midflight/private.json` into the corresponding worktree's ignored `.midflight/`
directory with permissions 0700 on the directory and 0600 on the file. Launch
`midflight agent --repo /path/to/backend-work --identity backend`. The launcher uses
that workspace for both Codex and MCP Git metadata. The identities still belong to
the same shared project. Do not rerun `init` with a different project identity for each
worktree. Generated MCP snippets contain absolute paths; regenerate/adapt their
`--repo` argument if configuring another client in a different worktree.

MidFlight doesn't merge branches, grant shared-file ownership or eliminate conflicts.
Normal review and integration testing remain necessary.

## Recovery and troubleshooting

- `midflight doctor --repo PATH --identity NAME` authenticates and prints current project
  context. It does not approve plans or claims. No approved plan is normal immediately
  after initialization; ask the lead to propose one.
- Connection refused: start the service and check `/healthz`, the URL and port. A healthy
  HTTP process alone is not proof of a completed review; inspect the claim/job status.
- Setup key missing: use the `--home` used by `serve`. The key must not enter Git or a
  prompt. Repeated initialization uses saved credentials and preserves existing files.
- Different setup/repository already registered: do not delete private config to retry.
  Keep or restore the original private config. Automatic lost-credential recovery and
  identity migration are not implemented.
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
- `.gitignore`: excludes `.midflight/` before credentials are written.
- `.midflight/private.json`: project URL/ID and separate lead/agent credentials.
- `.midflight/mcp-NAME.json`: client snippets pointing at the stdio adapter; no tokens
  in command arguments. Snippets are machine-local because paths are absolute.

No initial plan, example functions, artificial directives, generated code or global
client configuration is installed. Agent work is normal work in your repository.
