# GH-06: one project, four agent worktrees

This is separate from the commerce demo. The application is a small local task board:
create, list and complete tasks. All four agents work in Git worktrees of the same
new repository, sharing commits but keeping uncommitted working files separate.
The original MidFlight repository and the running demo are untouched.

| View | URL |
| --- | --- |
| New coding sessions | http://127.0.0.1:8937/ |
| New workspace/file observer | http://127.0.0.1:8947/ |
| New initialization controls | http://127.0.0.1:8937/graph |
| Existing commerce coding sessions | http://127.0.0.1:8907/ |
| Existing commerce file observer | http://127.0.0.1:8927/ |

## Start

```sh
uv sync --locked --extra falkordb --extra demo
uv run --extra falkordb --extra demo python -m midflight.theater.worktree_lab
# In another shell:
uv run --extra falkordb --extra demo python -m midflight.theater.source_view \
  --upstream http://127.0.0.1:8937 --port 8947
```

The first command launches four interactive sessions. Add `--paused` to create the
repository and empty plan without launching sessions; then use Start agents at
`8937/graph`. The observer is read-only and cannot start/reset agents.

Use a recent Codex CLI supporting named permissions profiles. To reattach the controller
after a process crash without resetting files, graph data or still-running tmux sessions:

```sh
uv run --extra falkordb --extra demo python -m midflight.theater.worktree_lab \
  --resume-run /absolute/path/to/worktrees-RUN_ID
```

Do not start two controllers for the same run. Normal shutdown intentionally closes its
owned terminals; reattachment does not resurrect a terminated Codex process. Agent
conversation histories are retained in the private per-agent profile directories.

Run directories are created under `~/.local/share/midflight-demo/worktrees-*/`:

- `repository/`: shared Git repository, with a starting `main` commit and no remote.
- `api/`, `web/`, `cli/`, `docs/`: linked worktrees on `agent-api`, `agent-web`,
  `agent-cli`, and `agent-docs`.
- `interactive.json` and `report.json`: session/project metadata. Launch profiles
  contain private session credentials and must not be published.

Reset from the new coding view archives that run and creates a new application
repository and worktrees. Earlier files and Git history remain in their run directory.

## Initial prompts

- API: “Build a Python API for the task board. Coordinate with MidFlight.”
- Web: “Build the task-board web interface. Coordinate with MidFlight.”
- CLI: “Build a CLI for the task board. Coordinate with MidFlight.”
- Docs: “Write setup instructions and an end-to-end smoke test. Coordinate with MidFlight.”

The initial plan contains the shared product goal and these four assignments.
**Contracts, provides and consumes all start empty.** No file ownership or API schema
is seeded. There is no subscription pivot, special lead session or prescribed chain
of dependencies. Initial prompts are assignments, not new product-direction changes.

The ordinary MidFlight claim/check-in protocol lives in MCP instructions, along with
Git workflow guidance. Short prompts do not imply the agents have no tool instructions.

## Coordination and code sharing

Every peer has the same capabilities:

1. Read the plan and other relevant coordination context.
2. Propose technical interfaces needed for its work, preserving unrelated context.
3. Declare provided/consumed fields in claims and handle directives/reviews normally.
4. Commit tested, approved work to its own branch.
5. Inspect peer commits with `team_branches` and `git show`; merge required peer commits
   into its own branch to integrate real implementations.

The controller accepts only active lab identities. It checks plan versions and
rejects stale updates. It allows tasks to be added, reassigned among the existing
four participants, and revised instead of enforcing the commerce fixture's fixed
task/owner/branch tuples. Standard plan validation still applies. This experiment
uses existing LEAD permission internally for every peer; none is privileged in the UI.
Product changes still require human direction under the agent instructions; that is
not independent cryptographic evidence of authorization enforced by the backend.

Plan versions and changes to committed file trees wake idle peers with a neutral
checkpoint prompt. Merge-only commits with identical file trees do not trigger another
round of check-ins. Busy sessions are not interrupted and typed drafts are preserved.
There is no predetermined recipient set: directives follow the actual declared plan,
and the graph links follow matching provider/consumer claims.

Sessions may stay alive between tasks. Give a new feature or direction in any window.
They must not reset/force-update another branch, edit another worktree's uncommitted
files, or push anything. A named Codex permissions profile permits writes to the agent's own worktree,
temporary directories, and the shared `.git` metadata. Ordinary workspace-write
protects Git metadata even with `--add-dir`, so this experiment uses explicit path
grants instead. Other worktrees remain read-only to shell commands. Git metadata is
shared, so the own-branch rule is still an agent instruction, not branch-level access
control. Each worktree has its own index. Commands have direct network access for
local HTTP servers and integration tests; the profile is not a network allowlist.
The initial `main` branch is not an automatic integration branch: review and integrate
real peer commits on an agent branch or a new developer branch.

## What the viewer proves

The file observer follows actual files in these worktrees. Files introduced through
merging another branch also appear, so a workspace association is not proof of which
agent authored a file. Initial README files are real starter files and are shown as
baseline state, not replayed as new writes.

Dashed arrows remain declared contract relationships, with exact field labels.
They are not a source-code import graph. No arrow exists before matching claims.
Agent acknowledgements and coordination approval do not prove the app works. App
acceptance requires actually running the resulting implementation and its tests.
The coordination page currently does not supply an independent task-board oracle.

Four physical agent sessions are provisioned. This is an unrestricted development
experiment within those workspaces, not arbitrary new-agent provisioning, production
multi-controller coordination, automatic publishing, or an unlimited model-usage loop.
All worktrees and model usage are local to this experiment; the old demo keeps running.
