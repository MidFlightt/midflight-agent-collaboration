# PigeonPost v6 benchmark setup

Three approaches build the same PigeonPost product with six agents, four fixed phases,
a late joiner, private developer notes, a fixed lead decision sheet and twenty product
checks. N has no channel; A uses a Git-backed team chat; B uses authenticated MidFlight
with an isolated local API and FalkorDB. This branch contains setup and tests only.

V6 removes redundant check-ins: join/send/object already return updates. Its bridge shares
repeated text **within each response**, with a response-local dictionary and exact decoding.
Every response is self-contained. Full policy history, current interfaces, pagination,
questions and open objections remain available. There is no incremental cross-response cache,
invalidation or on-demand retrieval experiment in this branch.

MidFlight owner publications establish versioned defaults immediately. Consumers may adapt
without acknowledgment. Objections name an exact publication/revision, concrete problem and
affected requirement/dependency; an alternative is optional. Only the objection author can
resolve it through structured send. Publications, tests and silence never resolve objections.
Unrelated work continues. MidFlight makes no model calls, wakes no idle agent and introduces
no reviewer or approval gate.

The runtime is pinned to commit `9d3ceae3040a18204a674ee7414356a20a2bdc16` and uses
`join`, `send`, `check_in`, `object`. It deliberately retains that API rather than the newer
upstream `objection` rename. Frozen source hashes record the complete runtime and harness.

## Requirements

Python 3.12+, uv, Git, Docker Compose, OpenSSL supporting `req -addext`, and authenticated
Codex CLI **0.162.1**. The model is **gpt-6.1-sol**, medium reasoning, default tier. The
chosen model must be available on your account. Auth must exist at `~/.codex/auth.json`;
isolated profiles link to it without copying it. macOS is the tested host; other hosts and
CLI versions need validation. Runs consume your own model allowance.

All arms use the same model, 50 completed tool items / 600 seconds per invocation, at most
three concurrent builders, fixed checkpoint opportunities and up to three repair rounds.
Those are tool/time limits, not a hard dollar/token cap. MidFlight adds no model invocations.

## Install and verify offline

```sh
git clone --branch codex/pigeonpost-benchmark-v6 https://github.com/MidFlightt/midflight-agent-collaboration.git
cd midflight-agent-collaboration
uv sync --locked --extra falkordb --extra demo
uv run pytest tests/unit/test_communication_benchmark.py tests/unit/test_benchmark_context.py tests/unit/test_benchmark_local.py
uv run python experiment/run.py pigeonpost X selftest
```

The self-test checks the reference fixture locally; it does not run coding agents.
The reference/scorer/private notes live outside each agent workspace. Agents receive only
their assigned task/notes and approach-specific channel instructions.

## Prepare a fresh local B backend

Use a new project ID for each independent B trial. Never reuse another team's project,
credentials, database or run directory. The commands below use dedicated Compose resources,
localhost API port 19483 and localhost database port 52017. If those ports are occupied,
stop and use a separate environment; do not stop or reconfigure someone else's service.

```sh
export PP_PROJECT=ppdemo001
export PP_CREDENTIALS="$HOME/.midflight-benchmarks/$PP_PROJECT"
uv run python -m experiment.communication.local --project "$PP_PROJECT" --credentials "$PP_CREDENTIALS"
docker compose -p "$PP_PROJECT" -f experiment/communication/compose.yaml up -d
```

Preparation creates seven distinct private agent tokens, a hashed server config and local
TLS files. It refuses to overwrite an existing setup and starts no service or agent. The
Compose project and volume belong to this trial. In a separate terminal, from this checkout:

```sh
unset MIDFLIGHT_CONFIG_JSON
export MIDFLIGHT_CONFIG="$HOME/.midflight-benchmarks/ppdemo001/config.json"
export MIDFLIGHT_DB_PORT=52017
uv run uvicorn midflight.communication.cloud:create_app --factory \
  --host 127.0.0.1 --port 19483 \
  --ssl-keyfile runs/local-backend/key.pem --ssl-certfile runs/local-backend/cert.pem
```

Clear any inherited `MIDFLIGHT_CONFIG_JSON` before starting: that variable takes precedence
over the config file. Keep this API terminal open. It authenticates every agent and seeds
only your configured project. Do not expose the database publicly or use a shared deployment.

Back in the first terminal, run the model-free coding-client preflight:

```sh
uv run python experiment/communication/client.py --output runs/client-preflight --credentials "$PP_CREDENTIALS"
```

It records exact model availability, CLI version, four-tool discovery and identity-rejection
probes. It starts no model turn and creates no benchmark dialogue. Check the recorded model
list and tool status before running. Preflight errors must be resolved, not ignored.

## Freeze and explicitly run one trial per approach

```sh
uv run python experiment/communication/prepare.py prepared/pigeonpost-v6 --project "$PP_PROJECT"
uv run python experiment/communication/run.py prepared/pigeonpost-v6 Ntrial1 --execute
uv run python experiment/communication/run.py prepared/pigeonpost-v6 Atrial1 --execute
uv run python experiment/communication/run.py prepared/pigeonpost-v6 Btrial1 --execute --credentials "$PP_CREDENTIALS"
```

Each command launches exactly one trial, including the fixed lead actions, actual merge,
scoring and any permitted repairs. There is no automatic scored campaign. Preparation starts
no agents and refuses overwrites. The runner requires --execute and verifies frozen hashes.
Failed/interrupted runs are preserved; it does not silently retry with a successful sample.
The narrowly scoped atomic-state harness-resume option is for diagnosis, not routine reruns.

To stop your own backend, interrupt its API terminal, then run:

```sh
docker compose -p "$PP_PROJECT" -f experiment/communication/compose.yaml down
```

This retains the database volume. Do not add `--volumes` when preserving evidence. For a new
independent B trial, use fresh project/credentials and a fresh local setup/checkout. Never
reset or overwrite a prior graph to reuse a trial ID.

## Evidence and privacy

Generated bundles, reports, credentials and raw logs are excluded from Git. Local trial
artifacts live under `prepared/.../runs/pigeonpost/RUN/`: state, original CLI streams,
per-call usage/status, prompts and backend traces. The operator snapshots each owned file
without changing agent code, merges the actual modules and runs unchanged score.py.
Input/cache/output usage is reported separately; resumed CLI usage is cumulative, so the
report differences snapshots by session ID. Unknown usage/cost remains unavailable.

Server routing, client delivery, explicit message references and applied code are distinct
evidence. Tests prove product behavior, not message consumption. Raw bridge results establish
transport receipt only. Review/redact logs before sharing them; never publish auth files,
tokens, session profiles or unreviewed transcripts. Subscription auth does not provide a
per-call dollar invoice. This setup makes no performance or effectiveness claim.
