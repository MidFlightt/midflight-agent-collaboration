# Cypher and graph algorithm used by MidFlight

The executable source is [dependency_graph.py](../../midflight/adapters/dependency_graph.py).
These are the actual read-query shapes used by impact analysis. Parameters come from
validated plan snapshots, never from an unrestricted agent-supplied Cypher string.

## Select a versioned snapshot

```cypher
MATCH (p:MFPlan {key:$key})
MATCH (g:MFPlanGraph) WHERE g.key=p.graph_key
RETURN g.key
```

`$key` is the canonical JSON encoding of `["Plan", project_id, version]`. The snapshot
key scopes all nodes below. A missing snapshot is an error, not an empty dependency set.

## Identify changed context nodes

```cypher
MATCH (n:MFContext)
WHERE n.scope=$scope AND n.item_id IN $changed
RETURN n.key,n.kind,n.item_id ORDER BY n.key
LIMIT $limit
```

See source for exact projection fields and limits. IDs are interpreted with their item
kind; both old and proposed snapshots are analyzed so removed edges remain explainable.

## Traverse the dependency frontier

```cypher
MATCH (a:MFContext)-[r]->(b:MFContext)
WHERE a.key IN $frontier AND b.scope=$scope
  AND type(r) IN ['PROVIDES','CONSUMED_BY','IMPLEMENTED_BY']
RETURN a.key,type(r),b.key,b.kind,b.item_id
ORDER BY a.key,type(r),b.key
LIMIT $limit
```

This is repeated as a bounded breadth-first traversal. A visited set handles cycles;
limits on depth, nodes and edges turn incomplete results into an explicit failure.
Stored paths retain item kinds, IDs, versions and relation names. A changed contract's
provider is also selected using the reverse-provider query:

```cypher
MATCH (t:MFContext)-[:PROVIDES]->(c:MFContext {key:$key})
WHERE t.scope=$scope
RETURN t.item_id
LIMIT $limit
```

Recipients are affected tasks that still exist in the proposed plan. Directives expose
why they were selected. A disconnected task is excluded. Before approval commits,
the database checks the analyzed snapshot keys and content alongside the project
revision, preventing stale graph analysis from approving changed state.

## Writes and atomicity

`projection_clauses()` in the same source creates `MFPlanGraph` and `MFContext` nodes,
`HAS_GRAPH`/`HAS_ITEM`, `IMPLEMENTED_BY`, `PROVIDES` and `CONSUMED_BY` edges. These clauses
are embedded in the guarded commit in
[falkor_store.py](../../midflight/adapters/falkor_store.py), alongside versioned entities,
idempotency receipt and audit events. Plans and their graph never synchronize through
a second store. See [dependency-graph.md](dependency-graph.md) for snapshot/key details
and [graph-propagation.md](graph-propagation.md) for approval guards.

Check the source when executing queries manually: some values are canonical composite
keys, not display IDs. Do not mutate projections through FalkorDB Browser while MidFlight
is running; that bypasses its versioning and integrity checks.
