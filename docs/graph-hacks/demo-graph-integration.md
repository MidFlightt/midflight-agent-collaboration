# GH-06 — Demo and graph propagation integration

This integration combines the demo with GH-05's graph-backed plan approval. The visual
demo remains owned by its existing branch; this branch adds acceptance evidence and
real-database coverage without changing the running demo's workspace or sessions.

The demo uses `create_server` with `store_backend="falkordb"`. Its plan approvals therefore
select direct and downstream recipients through `GraphPlanStore`; no second impact
calculation or manual list of recipients is needed in the controller.

The test uses the demo's actual seed and pricing-only change. Reporting's task and order
contract remain unchanged, but its check-in receives the saved path from Price through
Checkout and Order. Notifications receives no directive. This isolates graph traversal
from the subscription scenario, which also directly changes the order contract and tasks.

The Test evidence report now checks the current plan's Reporting directive, saved graph
explanations for all three affected tasks, and their acknowledgements. Old-version or
superseded directives cannot satisfy these checks. Acknowledgement means received, not
implemented; the separate application integration test remains required. The report
includes Reporting's actual directive records instead of the previous pending placeholder.

Run the database-backed acceptance test in an isolated Docker server:

```sh
uv run --extra falkordb pytest --falkordb tests/integration/test_theater_graph.py
```

These automated checks drive real services and database state; they do not launch coding
agents or establish that a combined live visual rehearsal has passed. A live run must
record the exact combined commit, verify the same four processes across the change,
inspect graph evidence in Reporting's check-in, and confirm Notifications' code is unchanged.
