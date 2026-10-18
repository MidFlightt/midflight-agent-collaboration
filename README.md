# MidFlight: communication between coding agents

Four real coding sessions use owner-published interfaces and receive relevant changes
through a FalkorDB dependency graph. MidFlight makes no model calls. There are no
claims, mandatory AI reviewers or approval gates. The tools are **join, send,
check_in, agree**. An owner's publication is the default immediately. Consumers
follow it without mutual acceptance. Explicit objections handle incompatibilities;
`agree` is optional for negotiated choices and never certifies code.

## Run the four-terminal prototype

```sh
uv sync --locked --extra falkordb --extra demo
docker compose -f compose.graph-hacks.yml up -d
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
uv run python -m midflight.communication.validate /absolute/path/to/run --label baseline --id-field id
uv run python -m midflight.communication.validate /absolute/path/to/run --fee 400 --label fee --id-field id
```

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
