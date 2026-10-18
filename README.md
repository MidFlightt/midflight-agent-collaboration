# MidFlight: communication between coding agents

[![Watch the MidFlight pitch and demo](https://img.youtube.com/vi/jv4e4_U-ygw/maxresdefault.jpg)](https://youtu.be/jv4e4_U-ygw)

**[▶ Watch the pitch and demo](https://youtu.be/jv4e4_U-ygw)**

[Watch the full end-to-end demo (no audio)](https://www.youtube.com/watch?v=LrAt4zUnVrc)

## The problem

Coding agents working on the same project can build incompatible interfaces or miss
requirements that change while they work. MidFlight gives them shared, versioned
interfaces and uses a FalkorDB dependency graph to route changes to the agents whose
work depends on them. The coding agents interpret requirements and write code;
MidFlight itself makes no model calls.

## Try it yourself

The local demo uses four agents: **Billing, Delivery, Booking and Notifications**.
Four is the demo configuration, not a limit on the coordination service.

You need Git, [uv](https://docs.astral.sh/uv/), Docker with Compose, `tmux`, and an
authenticated `codex` CLI on PATH. Python 3.12 or newer is required; uv can provision
it. The demo was tested on macOS with Codex CLI 0.162.1. Linux and other CLI versions
have not been verified; native Windows is not supported by this tmux harness.

Sign into Codex before starting. The harness expects credentials at
`~/.codex/auth.json`; keychain-only login and a custom `CODEX_HOME` are not supported.
The four sessions use your own Codex account and usage allowance.

### Start the demo

```sh
git clone --branch main https://github.com/MidFlightt/midflight-agent-collaboration.git
cd midflight-agent-collaboration
uv sync --locked --extra falkordb --extra demo
docker compose -f compose.graph-hacks.yml up -d --wait
uv run --extra falkordb --extra demo python -m midflight.communication.harness --port 18937
```

Keep this terminal running and open **http://127.0.0.1:18937**. Press Enter in each
of the four agent terminals to submit its prepared task.

Billing and Delivery start with incompatible list/mapping interfaces. Watch Delivery
publish its interface and Billing adapt or raise a concrete incompatibility.
Let the agents finish their initial work.

### Change a requirement

Send this to **Delivery**:

> When a delivery is cancelled, keep a four-credit cancellation fee and refund the rest, never below zero.

Let Delivery finish. The cancellation policy is routed to Billing and Delivery;
Booking and Notifications are not subscribed to it. Updates wait until an agent's
next useful task rather than automatically waking idle agents.

Then give **Billing** this follow-up:

> Add regression coverage for revenue reporting across mixed confirmed and cancelled deliveries under the current shared requirements, including small totals and previously saved refunds.

Watch Billing pick up the updated policy as it works.

### Check the combined code

Open **http://127.0.0.1:18937/report** to find the run directory. In another terminal,
from the repository directory, run:

```sh
uv run --extra falkordb --extra demo python -m midflight.communication.validate /absolute/path/to/run --fee 400 --label fee --id-field id
```

Replace `/absolute/path/to/run` with the directory shown in the report. If the agents
published `delivery_id` instead of `id`, use `--id-field delivery_id`. Use a new label
for each validation. Other negotiated API changes may require adapting the validator.
This checks the agents' actual combined Python modules; it does not test a deployed app.

**Reset** saves the previous run and prepares fresh, unsent tasks. Keep generated
`runs/` directories private: they contain local agent profiles. This prototype is
for local use; do not expose its terminal controller to the internet.
