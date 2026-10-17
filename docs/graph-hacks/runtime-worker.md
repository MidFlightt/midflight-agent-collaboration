# GH-03 — Runtime wiring and recoverable worker

Select `MIDFLIGHT_STORE=falkordb` to run the HTTP/MCP service against FalkorDB with
one in-process background worker. The worker scans saved jobs on startup and every
poll, so a crash between committing a job and notifying the worker does not lose it.

## Local setup

```sh
uv sync --locked --extra falkordb
docker compose -f compose.graph-hacks.yml up -d
cp .env.example .env
MIDFLIGHT_STORE=falkordb uv run --extra falkordb midflight-server
```

The sample configuration uses local development sign-in and a loopback-only database.
Use exactly **one server process per graph**. Do not add Uvicorn workers, overlapping
server instances or rolling deployments: distributed leases and fencing are outside
this implementation. Connect all coding agents to this one service.

The Compose volume persists database state across container restarts. Ordinary
`docker compose -f compose.graph-hacks.yml down` keeps it; `down -v` deletes it.
The image and durability settings match the persistence proof.

`MIDFLIGHT_STORE` accepts `memory`, `dynamodb` or `falkordb`. An explicit choice wins
regardless of `MIDFLIGHT_TABLE`. If unset, the existing table-or-memory selection is
preserved. DynamoDB requires a table. Invalid settings and unavailable FalkorDB fail
startup instead of falling back to an empty store. AWS's stream worker requires the
DynamoDB backend.

Connection variables are `MIDFLIGHT_FALKOR_HOST`, `PORT`, `GRAPH`, `USERNAME`,
`PASSWORD` and `SSL` (each with the `MIDFLIGHT_FALKOR_` prefix). SSL uses `1` to enable.
Do not expose the local unauthenticated database publicly.

## Processing and recovery

- Services commit a job with its claim or other changes before calling `submit`.
- `submit` only wakes the worker; it is not the durable queue.
- The worker scans queued and running jobs across projects and rereads each job.
- Before calling a handler, it saves `running`, increments attempts and timestamps it.
- Existing claim-review and verification handlers save their terminal result atomically.
- A thrown handler error queues a retry with a persisted error category and audit event.
- Default retry delay is 2 seconds, doubling between attempts, capped at 60 seconds.
  The delay uses the saved timestamp, so a restart preserves it.
- After three attempts, the job becomes failed with an audit event. Unfinished running
  jobs recovered at the attempt limit are failed instead of dispatching again.
- A handler's explicit succeeded/failed outcome is respected, including if the reply
  to its commit was lost. Domain failures (such as reviewer unavailable) require the
  existing lead retry workflow; the worker does not silently override them.

Settings: `MIDFLIGHT_WORKER_MAX_ATTEMPTS` (3), `MIDFLIGHT_WORKER_POLL_INTERVAL` (1 second),
`MIDFLIGHT_WORKER_RETRY_DELAY` (2 seconds). Poll errors are logged by exception category
and retried; they never become empty queue results. Handler error text is not persisted
because external errors may contain secrets. Jobs and their failure state remain visible
through existing job/check-in interfaces.

Handlers execute on a background thread, independently of request disconnection. Shutdown
stops accepting new jobs, wakes the poller and waits up to 30 seconds for the active handler.
If it does not stop, shutdown raises and keeps the connection open for that handler; a
process termination leaves its saved running job available for restart recovery. There
is no forced cancellation of an in-flight model call.

## Guarantees and limits

Execution is **at least once**, not exactly once. Existing idempotency receipts protect
local result commits. GitHub check publication is an external side effect: a crash after
publishing but before saving the result can cause another check publication on replay.
No cross-system transaction is claimed.

Claim reviews retain the existing project-revision check and recompute when context
changes. The worker does not alter the shared models or Store protocol; the FalkorDB
adapter supplies an additional operational unfinished-job scan. Scanning currently reads
all unfinished jobs and dispatches at most 100 per poll, appropriate for the small demo.

Tests cover missed notifications, running-job recovery, durable bounded retry/backoff,
ambiguous success, poll outages and lifecycle. Real-database tests exercise database
SIGKILL/restart followed by a fresh store/worker, service startup/shutdown, and context
changes during a review. The restart test simulates an interrupted dispatch by saving a
running job; it does not kill an actual model call mid-execution.

```sh
uv run --extra falkordb pytest --falkordb
```

Task/contract graph materialization, graph impact traversal and the four-agent demo
remain subsequent work.
