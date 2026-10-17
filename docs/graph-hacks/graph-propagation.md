# GH-05 — Graph-based directives and check-ins

FalkorDB plan approval now uses the dependency queries to choose direct and downstream
recipients. Memory and DynamoDB retain their direct-impact behavior. Graph errors never
trigger a fallback to direct-only analysis. Services use the optional `GraphPlanStore`
protocol in `midflight/graph_ports.py`; the shared Store and domain models are unchanged.

## Approval sequence

1. Read the project and draft, and recompute the changed IDs against the current plan.
2. Analyze the old and proposed plan graphs separately. The proposed graph must match
   the draft content just read; a changed draft causes a reread/retry.
3. Build directives only for affected tasks present in the new plan. Supersede older
   actionable directives for those tasks. Reset affected approved claims to pending and
   create their durable re-review jobs; unaffected tasks and claims remain unchanged.
4. In one atomic write, validate the project revision **and** each analyzed plan's exact
   graph snapshot, then save approval, directives, claims, jobs and audit events.
5. Notify the runner only after that write succeeds. A concurrent duplicate approval
   returns a conflict and never dispatches its locally constructed, unsaved jobs.

Snapshot comparison is a database guard inside the commit query, not a preflight read.
The adapter also checks that the Plan being approved has the analyzed content. This
protects the gap between analysis and commit even though draft proposals do not bump
`coord_rev`. Initial plan approval also guards its proposed snapshot.

A revision or snapshot change retries from fresh state up to the existing approval limit.
Missing projections or incomplete traversal return a service conflict with the analysis
error, leaving the plan unapproved. Database errors propagate. A lost response after a successful commit may leave the
approval saved; durable jobs remain recoverable and the approval receipt prevents a
second write. IDs allocated while preparing a rejected attempt may leave gaps.

## Evidence delivered to agents

Versioned graph paths are persisted in the existing directive `reason` field alongside
the lead's explanation. Identical paths from old and new plans are grouped and labeled
with both versions. Removed dependencies retain their old-version evidence. Paths explain
potential impact; they do not assert that every downstream task must change code.

For example, Reporting receives a reason containing:

```text
Graph evidence (plan v2, v3): contract price -CONSUMED_BY-> task checkout -PROVIDES-> contract order -CONSUMED_BY-> task reporting.
```

The existing check-in service returns this evidence in its directive JSON. Both hosted
and local MCP rendering display it in the directive's `Why` text. Fresh sessions receive
the full reason; a continuing session using its previous marker retains existing compact
reply behavior. Evidence remains part of directive data, not a system instruction.
No graph query is needed at delivery time: the reason records the approved snapshots.

An unrelated Notifications task receives no change directive. Existing acknowledgement,
stale-state holding, ownership checks and push blockers remain in force.

## Validation and limits

Real-database integration tests cover downstream directives, check-in/MCP evidence,
fresh-session replay, unaffected tasks, durable re-review jobs, missing/incomplete graphs,
draft edits between analysis and commit, rollback of invalid snapshot guards, and competing
approvals without duplicate job dispatch. The existing store/service/MCP suites remain active.

The graph's traversal limits and single-process worker limits still apply. This does not
add graph evidence to AI review prompts or introduce a new MCP tool. A real four-agent
rehearsal and independent application integration test remain next.
