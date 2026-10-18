# MidFlight: communication between coding agents

**Keep a team's coding agents in sync as interfaces and requirements change.**
MidFlight connects four real coding sessions through a FalkorDB dependency graph,
so a change reaches the agents whose work depends on it.

## For judges

**[Watch the submitted pitch and demo](https://youtu.be/jv4e4_U-ygw)** ·
[Run the prototype](#run-the-four-terminal-prototype) ·
[Inspect the measured evidence](docs/evidence/object-rehearsal.md) ·
[Read the architecture](docs/agent-communication.md)

### The problem and the demo

Coding agents working on separate parts of a project can build incompatible
interfaces or miss a requirement that changes after work begins. MidFlight gives
them shared, versioned interfaces and routes relevant updates through explicit
dependencies.

The demo uses **Billing, Delivery, Booking and Notifications**:

1. Billing and Delivery begin with incompatible list/mapping interfaces. Delivery
   publishes the interface it owns; Billing can adapt or raise a concrete incompatibility.
2. A human asks Delivery to retain a four-credit cancellation fee. Delivery publishes
   the new policy without changing the API shape.
3. The graph routes the policy to Billing and Delivery. Booking and Notifications
   are not subscribed to cancellation policy and receive no fee update.
4. Billing receives the pending policy when it next does useful work. The operator
   separately tests the four agents' actual combined Python modules.

### Why FalkorDB matters

Agents subscribe to topics, and topics can depend on other topics. FalkorDB stores
this dependency graph and selects subscribers of a changed topic and its transitive
dependants. Keeping business policies separate from API shape lets a cancellation
rule reach Billing without notifying every consumer of Delivery's interface.
Versioned publications, retry receipts and per-session inbox cursors persist with
the coordination state. Coding agents interpret requirements and write code;
**MidFlight itself makes no model calls**.

### What was demonstrated

The [latest documented real-agent rehearsal](docs/evidence/object-rehearsal.md)
records interface adaptation, selective fee routing, **23 component tests and an
operator-run combined-code test passing after Billing's follow-up**, with zero
automatic wakeups or repeated nudges. Booking and Notifications' code and session
state remained unchanged during the fee stage.

This is one rehearsal, not a reliability or speedup benchmark. No formal objection
occurred in that run; the objection lifecycle is covered by focused tests. Combined
validation covers Python modules, not a deployed application. The evidence separates
routing, delivery, observed use and test results.

### The four coordination tools

| Tool | Purpose |
| --- | --- |
| `join` | Join a project session and declare topic subscriptions. |
| `send` | Publish an owned interface or policy, or communicate with peers. |
| `check_in` | Retrieve relevant updates at a natural work checkpoint. |
| `object` | Record a concrete incompatibility with an exact interface or policy revision. |

An owner's publication takes effect immediately; consumers follow it without
mutual acceptance. Only the objection author can resolve their objection through
`send`. Silence is neither agreement nor proof of compatibility. There are no
mandatory AI reviewers or approval gates.

## Run the four-terminal prototype

This is the hackathon prototype in **MidFlightt/midflight-agent-collaboration**.
Use **`main`** for the current review and local setup. The previously submitted
[`codex/agent-communication` link](https://github.com/MidFlightt/midflight-agent-collaboration/tree/codex/agent-communication#run-the-four-terminal-prototype)
remains available. The official MidFlight repository is separate.

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
git clone --branch main https://github.com/MidFlightt/midflight-agent-collaboration.git
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
