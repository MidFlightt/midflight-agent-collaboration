# Measured rehearsal results — 2026-10-17

For the subsequent owner-publication and no-wakeup work, see
[the follow-up measurements](published-interfaces.md). The results below describe
the earlier agreement-based migration.

Two actual four-terminal Codex runs were executed. The CLI used its configured
default model, displayed as GPT-6.1-Sol. Agents wrote and tested the component code;
the operator combined their owned modules without editing their implementations.

The **corrected run** is in `communication-2026-10-17-corrected`. Its initial
incompatible list/mapping starters converged on a list interface. All participants
explicitly agreed. Baseline: 28 component tests and the combined workflow pass.
Fee change: 29 component tests and the combined workflow pass.

| Agent | Initial turn seconds | Fee turn seconds | Explicit check_in calls across both stages |
| --- | ---: | ---: | ---: |
| Billing | 35.971 | 14.386 | 3 |
| Delivery | 47.404 | 19.046 | 2 |
| Booking | 54.960 | no turn | 2 |
| Notifications | 30.307 | no turn | 1 |

Times are CLI task-start/task-complete timestamps, not coordination latency or a
controlled benchmark. Check-in counts are extracted requested tool calls in saved
CLI call source; send/join/agree also return inbox updates. There was one neutral
operator notification to Billing after the fee policy existed, and no idle polling.

Fee event 17 and applied reports 18/19 all have exactly Billing and Delivery as
recipients. Booking and Notifications module hashes match their baseline snapshots;
neither received a further coding turn. Billing's production module also stayed
unchanged: its saved-refund calculation already handled retained fees. Its agent
added verification; Delivery changed production code and tests.

The **first run** is retained in `communication-2026-10-17`. It negotiated a mapping
instead of a list and passed its code tests, but Delivery explicitly addressed an
applied report to Booking. That was a real routing failure despite unchanged Booking
code and no Booking wake-up. The fix rejects policy reply audience expansion. The
corrected run above demonstrates selective communication after the fix.

Validation commands executed:

- `pytest --falkordb -o addopts='' -q`: **558 passed in 12.92s**, including the real
  database suite and eight new communication/MCP tests.
- `ruff check .`: passed. Evidence code is excluded so its original bytes remain intact.
- `git diff --check`: passed.
- Untouched behavioral source: **37 passed in 7.53s**.
- Isolated database SIGKILL/restart: receipts, cursors and pending policy recovered.
- Actual controller SIGKILL/`--resume`: same graph, tmux session and 19 events recovered.
- Actual reset: archived prior code and graph, created fresh graph, prepared four unsent prompts.
  A browser reset was also exercised after the corrected run.

Limitations: only two rehearsals, no model or token-cost comparison, trusted local
identities, agent-attributed human sources, manual wake-up for an idle peer, whole
project snapshot CAS storage, and no production-scale load/failover test. Tests do
not establish a full deployed browser end-to-end implementation. The policy routing
check is structural; arbitrary text in an unrelated peer message is not semantically
classified by MidFlight.
