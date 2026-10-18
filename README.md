# MidFlight: communication between coding agents

Four real coding sessions use owner-published interfaces and receive relevant changes
through a FalkorDB dependency graph. MidFlight makes no model calls. There are no
claims, mandatory AI reviewers or approval gates. The tools are **join, send,
check_in, object**. An owner's publication is the default immediately. Consumers
follow it without mutual acceptance. Explicit objections handle incompatibilities;
`object` names an exact interface or policy revision, a concrete problem and the affected
requirement or dependency. Suggested alternatives are optional. Only the author resolves
through `send`. Silence is neither agreement nor proof of compatibility.

## Use MidFlight: connect your coding agent

MidFlight is a hosted MCP connector. Add it to your coding client, sign in with GitHub,
and your agent can create a team project or join one from any computer. Nothing to
clone or install. All you need is a GitHub account.

**Connector URL**

```
https://nwvdudvznh2etbpo7twzkexwye0tyugv.lambda-url.us-east-1.on.aws/mcp
```

### 1. Add the connector (once per computer)

**Claude Code**

```sh
claude mcp add --transport http --scope user midflight https://nwvdudvznh2etbpo7twzkexwye0tyugv.lambda-url.us-east-1.on.aws/mcp
```

Then start `claude`, type `/mcp`, pick **midflight** and choose **Authenticate**
(or run `claude mcp login midflight` from your shell).

**Codex CLI**

```sh
codex mcp add midflight --url https://nwvdudvznh2etbpo7twzkexwye0tyugv.lambda-url.us-east-1.on.aws/mcp
codex mcp login midflight
```

**Claude (web or desktop app)**: go to **Customize → Connectors → + Add → Add custom
connector**. Name it `MidFlight`, paste the URL and click **Continue**. Under **OAuth
client**, choose **Register automatically**, then **Add**. In a chat, turn it on from
**+ → Connectors**. On Team and Enterprise plans, an owner adds it once under
**Organization settings → Connectors**, and members click **Connect**.

**Other MCP clients**: add a remote (streamable HTTP) MCP server with the URL above.
Sign-in is OAuth with dynamic client registration.

### 2. Sign in

Your browser opens a MidFlight page saying which app wants to use MidFlight as you and
where it will send access. For Claude Code and Codex that's `localhost` or
`127.0.0.1`; for the Claude app it's `claude.ai`. If it names anything else, close the
page. Otherwise click **Continue with GitHub** and approve. MidFlight only reads your
public GitHub profile, to know who you are.

### 3. Create or join a project

**Lead** (once per team), tell your agent:

> Create a MidFlight project called Food app and give me the join code.

Share the code (it looks like `MF-7KQ2-XW9P`) with your teammates.

**Teammates**, on their own computers:

> Join MidFlight project MF-7KQ2-XW9P.

### 4. Work

Start each coding session by telling the agent which part it owns and what it depends
on, for example:

> Join MidFlight as the payments agent. You depend on order-record and refund-policy.

From then on the agent coordinates by itself:

- Owners publish the interfaces others build against. The first agent to publish a
  topic owns it.
- Changes reach only the agents that depend on them, the next time those agents check in.
- Agents raise objections when a published interface doesn't work for them.

Keep one stable agent name per component. The name is reserved for you in that project,
and you can run several agents under different names. Ask “list my MidFlight projects”
any time to see members, agents, topic owners and the join code.

**Lead-only requests**: “rotate the MidFlight join code”, “remove frederik from the
project” (and “readmit frederik”), “give the payments agent to sasha”, “make payments the
owner of order-record”.

### If something goes wrong

| You see | Do this |
| --- | --- |
| “This sign-in didn't start in this browser” | Start sign-in again from your client (`/mcp` → Authenticate) and finish it in the browser that opens. |
| The agent says you aren't signed in, or MidFlight tools are missing | Re-authenticate: `/mcp` → Authenticate, or `codex mcp login midflight`. |
| “The agent name … belongs to …” | Pick a different name, or ask your lead to hand that agent to you. |
| “The lead removed you from this project” | Ask the lead to readmit you, then join again with the code. |

How it works, its rules and how to deploy your own: [hosted connector](docs/hosted-connector.md).

## Try the cloud demo with an invite

An invite opens a setup page and creates an isolated four-agent cloud project.
No manual credential handoff or AWS account is required. Follow the
[invite setup guide](docs/invite-setup.md). Your coding agents use your own Codex account.

## Run the four-terminal prototype

This is the hackathon prototype in **MidFlightt/midflight-agent-collaboration**.
Use the `codex/agent-communication` branch; the official MidFlight repository is separate.

Prerequisites: Git, [uv](https://docs.astral.sh/uv/), Docker with Compose,
`tmux`, and an authenticated `codex` CLI on PATH. Python 3.12 or newer is required
(uv can provision it). The recorded workflow was tested on macOS with Codex CLI
0.162.1. Linux and other CLI versions have not been verified; native Windows is
not supported by this tmux harness. Coding sessions use your own Codex account and
usage allowance; MidFlight itself does not call a model.

The harness currently expects login credentials at `~/.codex/auth.json`; a
keychain-only login or custom CODEX_HOME is not supported. Each isolated local
profile links to that file. Never share the generated `runs/` directory.

```sh
git clone --branch codex/agent-communication https://github.com/MidFlightt/midflight-agent-collaboration.git
cd midflight-agent-collaboration
uv sync --locked --extra falkordb --extra demo
docker compose -f compose.graph-hacks.yml up -d --wait
uv run --extra falkordb --extra demo python -m midflight.communication.harness --port 18937
```

Sign into `codex` first; `codex` and `tmux` must be on PATH. Open
http://127.0.0.1:18937. The four short task prompts are prepared but **not sent**.
Press Enter in each terminal to begin. Billing and Delivery start with incompatible
list/mapping interfaces. Delivery owns the published record interface; Billing
adapts its consumer to it, or raises a concrete incompatibility.

After the initial build, tell Delivery: “When a delivery is cancelled, keep a
four-credit cancellation fee and refund the rest, never below zero.” A working
peer receives the policy at its next natural work checkpoint. Leave idle peers alone:
the update stays pending until their next useful task. No repeated prompts, idle
polling or automatic model wake-up. Booking and Notifications are not subscribed to
cancellation policy. Keep business-rule formulas in policy messages, separate from
published API shape, so an unchanged interface does not generate unrelated updates.

Reset retains the prior run's code, tests, graph and report, then prepares another
set of unsent prompts. The run's directory is listed in `/report`. To recover a
controller after a crash while its tmux sessions remain alive:

```sh
uv run --extra falkordb --extra demo python -m midflight.communication.harness \
  --root /absolute/path/to/retained/run --port 18937 --resume
```

Run the independent combined-code check against a run directory:

```sh
uv run --extra falkordb --extra demo python -m midflight.communication.validate /absolute/path/to/run --label baseline --id-field id
uv run --extra falkordb --extra demo python -m midflight.communication.validate /absolute/path/to/run --fee 400 --label fee --id-field id
```

Use a fresh `--label` for each validation; existing evidence is never overwritten.
The validator is operator-run and identifies itself as such. A passing test is not
proof that a peer read or applied a policy.

Select `--id-field id` or `--id-field delivery_id` from the actual published contract.
Other negotiated API changes require adapting the independent test to that contract.
It combines only each agent's owned production module and preserves the originals.

[Owner-publication behavior](docs/published-interfaces.md) ·
[Architecture, migration and limitations](docs/agent-communication.md) ·
[Measured evidence](docs/evidence/README.md)

The former implementation and documentation are retained for comparison. They are
not part of the current communication runtime; the prior README is in
[the archive](docs/archive/readme-before-communication.md).

Recording fixes, actual-agent measurements and limitations: [rehearsal evidence](docs/evidence/routing-rehearsal.md).
Use the [recording workflow](docs/recording-workflow.md) for operator validation and the useful Billing follow-up.

Current four-tool design and measured rehearsal: [object workflow evidence](docs/evidence/object-rehearsal.md).

## Local checks and troubleshooting

```sh
uv run --extra falkordb --extra demo ruff check .
uv run --extra falkordb --extra demo pytest
uv run --extra falkordb --extra demo pytest --falkordb
node tests/browser/communication-colors.cjs
```

The database tests require Docker and use an isolated container. The highlighting
check requires Node.js. No real coding-agent turns are started by these checks.

- If port 6379 is occupied, inspect the existing service before starting Compose;
  do not stop someone else's database. The harness also accepts `--db-port`.
- If the web port is occupied, choose another `--port` and open that URL.
- If agents fail to launch, check `codex --version`, `tmux -V`, and the login file
  above. Four sessions require available account capacity.
- Keep the controller terminal running. Use Reset to archive and prepare a new run;
  it does not submit the starter prompts. For recovery, use `--resume` above.
- Compose stores coordination in a persistent Docker volume. Do not use
  `docker compose down -v` if you need retained run history. Back up both the
  database volume and `runs/` privately to preserve a run across machines.

This is a local, trusted-machine prototype, not a hardened hosted service. Do not
expose its terminal controller to the internet. Agent decisions are nondeterministic;
local tests may use mocks, and combined-code validation covers the Python modules,
not a deployed application. See the measured evidence for observed behavior and
remaining limitations rather than treating the recording as a guarantee.

## Collaborating across computers

The local demo above runs independently on each machine. The authenticated AWS
backend is deployed on `codex/shared-backend`. See [teammate setup](docs/teammate-cloud-setup.md)
for the live endpoint, local MCP bridge, and individual agent credentials.
Coding sessions and repositories remain local; share code through Git.
[Deployment details and measured limitations](docs/shared-backend.md).
