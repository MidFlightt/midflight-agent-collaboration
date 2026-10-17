# Native dependencies in the peer/worktree demo

This branch integrates the native dependency model already merged into the hackathon
repository with the newer equal-peer and four-worktree experiments. It preserves both
sets of work. The official MidFlight repository is unchanged.

## What runs now

```text
MFPlan --HAS_GRAPH--> immutable MFPlanGraph snapshot
                       └─ HAS_ITEM --> MFContext nodes (task, contract, requirement)

task --PROVIDES--> contract --CONSUMED_BY--> consuming task
requirement --IMPLEMENTED_BY--> task
```

Each context node belongs to exactly one project, version and content hash. Full plan
and claim JSON remain stored. Projections and coordination writes share the existing
atomic commit and approval snapshot guards.

**FalkorDB computes reachability and evidence paths using shortestPath.** Python does
not run the earlier breadth-first adjacency loop. It checks budgets and converts
returned paths into domain values. A changed contract's provider is selected separately
through a native reverse-PROVIDES query; that does not incorrectly propagate into the
provider's other outputs. Changed tasks select themselves explicitly.

The executable parameterized Cypher is NATIVE_IMPACT_QUERY in
`midflight/adapters/dependency_graph.py`. Old and new snapshots are queried independently.
Current-task filtering excludes removed tasks from delivery. Cycles terminate; one
shortest explanation is retained per changed item/task/version. A native
PROVIDES/CONSUMED_BY join in FalkorStore.dependency_links drives viewer arrows.

Budgets apply to **each whole context** before traversal: at most max_nodes nodes
(default 1000) and max_edges dependency edges (default 5000). Evidence paths may have
at most max_depth edges (default 32). Exceeding a budget raises IncompleteImpact;
no partial result approves a plan. Database errors propagate with no JSON/Python
reachability fallback. This is stricter than the previous reachable-frontier budget.

PlanService creates directives and review jobs from the graph result. Existing
permissions, project CAS, draft snapshot guards and idempotency checks remain in charge.
Downstream-only directives ask for a **potential impact review**, not an assumed code
or output-contract change. Versioned paths appear in directive reasons/check-in output.

## Existing data and demo sessions

On startup, FalkorStore materializes plans lacking graph_key through the same atomic
commit guards. Payloads and coordination revisions remain unchanged. Old graph snapshots
are retained; draft-context garbage collection is deferred. Migration failures prevent
startup instead of becoming an empty graph.

Run only one service/worker per graph. Never attach another active controller to a live
run's graph. A stopped worktree lab can use --resume-run to reattach preserved workspaces
and tmux sessions. Do not use Reset to upgrade ongoing work.

The existing demo sessions were not stopped or reset. Start an isolated paused run:

```sh
uv sync --locked --extra falkordb --extra demo
uv run --extra falkordb --extra demo python -m midflight.theater.worktree_lab \
  --port 18947 --api-port 18948 --paused
uv run --extra falkordb python -m midflight.theater.source_view \
  --upstream http://127.0.0.1:18947 --port 18957
```

The lab begins with assignments and no contracts. Agents declare contracts through
normal plan publishing. /graph-state includes native_dependencies and dependency_evidence.
The viewer draws native links only once their agents have appeared. File nodes still
reflect filesystem observation: source code is not stored in FalkorDB, and a link does
not prove code compatibility or passing tests.

## Verification

```sh
uv run --extra falkordb pytest --falkordb
node tests/browser/source-graph.cjs
uv run ruff check .
uv run ruff format --check .
```

Existing graph tests cover isolation, removed links/tasks, cycles, limits, rollback,
stale drafts, concurrent approval and check-in delivery. Added database tests verify
shortestPath use, no Python impact fallback, native-edge authority despite unchanged
JSON, viewer joins, startup migration, restart recovery and a lab growing from no contracts.
