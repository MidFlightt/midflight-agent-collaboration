# GH-04 — Versioned task/contract graph and impact queries

Plan commits now materialize tasks, contracts, requirements and their relationships
in the same guarded Cypher write as the plan, its audit events and retry receipt.
There is no second database or asynchronous graph-sync step.

## Graph structure

`MFPlan` selects its current projection through `graph_key`. An `MFPlanGraph` snapshot
contains `MFContext` nodes whose `kind` is `task`, `contract` or `requirement`. Each
node retains its item ID and structured JSON. The key includes the project, plan
version and a SHA-256 digest of that version's task/contract/requirement content.

Relationships are:

- `MFPlan -HAS_GRAPH-> MFPlanGraph -HAS_ITEM-> MFContext`
- Task `-PROVIDES->` Contract
- Contract `-CONSUMED_BY->` Task
- Requirement `-IMPLEMENTED_BY->` Task

Both task declarations and contract provider/consumer lists contribute edges;
identical edges are deduplicated. Unknown references and duplicate IDs within an
item kind reject the entire commit. Free-text assumptions do not create dependencies.

Snapshots are immutable. Replacing a proposed plan selects a new snapshot, so old
edges cannot remain active accidentally. Old draft snapshots are retained; garbage
collection is not included. Approval of an unchanged draft selects the same graph.
Approved-plan history retains the Store's existing immutability protection.

## Query API

```python
result = store.dependency_impact(
    project_id,
    old_version,
    new_version,
    changed_ids,
    max_depth=32,
    max_nodes=1000,
    max_edges=5000,
)
result.affected_tasks  # task ID -> sorted changed IDs
result.paths  # version, changed ID, target task, nodes, relationships
result.snapshots  # exact snapshot keys used in the analysis
```

Compute `changed_ids` with the existing pure plan comparison. For a single-version
analysis, pass that version as both old and new. Only tasks present in the new plan
are recipients; old-version nodes can still explain why a surviving task is affected.

A changed contract affects its provider directly and follows consumers downstream.
Its provider edge is recorded as `PROVIDES_REVERSE` in evidence; it is not followed
into unrelated outputs of that provider. Changed tasks follow all their outputs;
changed requirements follow implementing tasks and their outputs. These are potential
review targets, not assertions that every task needs code changes.

For the four-task example, changing `price` yields Pricing, Checkout and Reporting,
with the downstream path:

`price -> Checkout -> order -> Reporting`

Notifications receives no impact. Each path names the plan version supporting it.

## Traversal and completeness

Parameterized Cypher queries expand one frontier at a time over stored relationships.
The Python coordinator keeps visited node keys and one shortest forward path per
source/recipient/version. It is a breadth-first traversal, not a scan of JSON plans.
Cypher filters target nodes to the selected snapshot at every step. Old and new
versions are traversed independently, then their results are combined; no path can
join an old edge to a new edge. Provider evidence is handled separately.

The limits bound depth in graph edges, visited nodes per source, and total expanded
edges across both versions and all sources. Seed and recipient counts are also bounded.
Queries request one extra edge/row to detect truncation. Hitting a limit raises
`IncompleteImpact`; no partial result is returned as complete. Cycles terminate via
the visited set. Database errors propagate. Limits bound returned traversal work,
not a benchmarked database execution-time guarantee.

A missing plan/projection raises `GraphNotReady`; unknown changed IDs raise `ValueError`.
A draft graph pointer changing during analysis raises `GraphChanged`, requiring fresh
plan reads and another query. The result still represents the named snapshots: a future
approval integration must guard its final write against any changes after the query.
[GH-05](graph-propagation.md) now routes plan-change directives through these queries
and guards the analyzed snapshots in the approval write.

## Existing data

New plan writes materialize automatically. For a plan approved before GH-04:

```python
store.materialize_approved_plan(project_id, version)
```

This idempotent backfill uses the normal atomic commit, preserves coordination revision
and approved content, and adds the graph projection. It only accepts approved plans;
replace an old proposed draft through the normal propose workflow to materialize it.
Backfill is explicit, never silently interpreted as an empty dependency graph.

## Validation and remaining work

Real-FalkorDB tests cover direct/downstream impact, unrelated tasks, removed links and
tasks, cycles, limit errors, missing graphs, unknown changes, requirement propagation,
project isolation, draft replacement and concurrent draft edits, atomic engine rollback,
backfill and version separation. CI runs them alongside the store and worker suites.

GH-05 creates scoped directives and re-review jobs atomically and includes evidence
in check-ins. AI review-context enrichment and the four-agent demonstration remain.
The shared models and Store protocol are unchanged; result types live in `domain/graph.py`.
