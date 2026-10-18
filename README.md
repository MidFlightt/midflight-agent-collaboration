# MidFlight: communication between coding agents

Four real coding sessions negotiate shared interfaces and receive relevant changes
through a FalkorDB dependency graph. MidFlight makes no model calls. There are no
claims, mandatory AI reviewers or approval gates. The tools are **join, send,
check_in, agree**. Agreement records an exact revision accepted by participants;
it does not certify their code.

## Run the four-terminal prototype

```sh
uv sync --locked --extra falkordb --extra demo
docker compose -f compose.graph-hacks.yml up -d
uv run --extra falkordb --extra demo python -m midflight.communication.harness --port 18937
```

Sign into `codex` first; `codex` and `tmux` must be on PATH. Open
http://127.0.0.1:18937. The four short task prompts are prepared but **not sent**.
Press Enter in each terminal to begin. Billing and Delivery start with incompatible
list/mapping interfaces; the agents choose how to resolve them.

After the initial build, tell Delivery: “When a delivery is cancelled, keep a
four-credit cancellation fee and refund the rest, never below zero.” A working
peer receives the policy at its next checkpoint. If Billing has finished its turn,
tell it that a MidFlight message is waiting. There is no idle polling or automatic
model wake-up. Booking and Notifications are not subscribed to cancellation policy.

Reset retains the prior run's code, tests, graph and report, then prepares another
set of unsent prompts. The run's directory is listed in `/report`. To recover a
controller after a crash while its tmux sessions remain alive:

```sh
uv run --extra falkordb --extra demo python -m midflight.communication.harness \
  --root /absolute/path/to/retained/run --port 18937 --resume
```

Run the independent combined-code check against a run directory:

```sh
uv run python -m midflight.communication.validate /absolute/path/to/run --label baseline
uv run python -m midflight.communication.validate /absolute/path/to/run --fee 400 --label fee
```

This validator tests the delivery-ID record shape used in the measured rehearsal;
if agents negotiate a different shape, update the test against that explicit contract.
It combines only each agent's owned production module and preserves the originals.

[Architecture, migration and limitations](docs/agent-communication.md) ·
[Measured evidence](docs/evidence/README.md)

The former implementation and documentation are retained for comparison. They are
not part of the current communication runtime; the prior README is in
[the archive](docs/archive/readme-before-communication.md).
