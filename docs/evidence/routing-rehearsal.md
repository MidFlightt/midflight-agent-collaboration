# Routing and recording rehearsal, 2026-10-17

Started from clean `411f939` on `codex/agent-communication` in the collaboration
repository. Original GH-05 preserved-file hashes still match `preservation.json`.
No edits were made to the official repository or original Midflight source checkout.
Prior runs and terminals were preserved.

## Fixes

Topic updates cannot use explicit recipients to bypass or narrow the dependency graph.
Topic replies cannot relabel their topic or override audiences. Direct messages remain
available without a topic; optional proposals keep explicit participants. Publications
linked to a private discussion still reach all current subscribers.

Only the latest policy revision is actionable. Older revisions retain exact IDs,
superseding IDs, original bodies and application reports; supersession is not handling.
Policy bodies emitted as context now have independent durable per-session delivery IDs.
The focused tests cover database crash/restart, retry idempotency, exact old/new reports,
new independent sessions, transitive routing and prohibited audience overrides.

Validation explicitly attributes execution to the operator and separates local component
suites (which may mock peers) from copied actual modules tested together. Saved validation
includes exact module hashes; reports flag when these no longer match current code.
The existing CLI already failed on component failures at 411f939; that was preserved.
Agent instructions now identify local peer files as starter snapshots and prohibit
claiming end-to-end success from local tests. No reviewer or approval gate was added.

## Measured run

Run: `runs/routing-rehearsal`; graph `communication-ee2e78f3b48941df8bd934a9a03d5bd4`.
The operator started Delivery first, then the other prepared tasks after its publication.
Billing's starter expected lists; Delivery published an ID-keyed mapping in event 1.
Billing adapted its actual `revenue_report()` to that mapping, retaining list support
for existing callers. This was owner publication followed by adoption, not a staged
mutual-agreement negotiation. There were no proposals, agreements or objections.

| Measurement | Result |
| --- | --- |
| Initial turns: Delivery / Billing / Booking / Notifications | 33.3 / 33.3 / 54.4 / 32.4 seconds |
| Fee turn: Delivery | 16.0 seconds |
| Useful follow-up: Billing | 18.4 seconds |
| Explicit check_in calls over all turns | Billing 1, Delivery 2, Booking 1, Notifications 0 |
| Baseline local tests | 24 passed |
| Baseline actual combined test | passed, operator executed |
| Fee while Billing still idle | actual combined test passed; **not** consumption evidence |
| After Billing follow-up | 27 local tests + actual combined test passed |
| Coordination events | 11 |
| Automatic wakeups / repeated nudges | 0 / 0 |

The operator submitted the human fee only to Delivery. Delivery interpreted four credits
as 400 cents and published policy 9 on `cancellation-policy`; the API stayed at its
original revision. Delivery's report 10 references policy 9. The intermediate snapshot
shows Billing had not received policy 9 in any session and had not reported application,
even though the assembled test passed.

The operator then submitted exactly one useful Billing task: “Add regression coverage
for revenue reporting across mixed confirmed and cancelled deliveries under the current
shared requirements, including small totals and previously saved refunds.” Billing
checked in, added coverage for saved historical refunds and fee boundaries, and sent
report 11 referencing policy 9. Its report explicitly says local tests use mocks and
leaves integration validation to the operator. Billing required no production-code change.

| Agent | Policy 9 routed | Server-delivered | Evidence of reading | Application evidence |
| --- | --- | --- | --- | --- |
| Delivery | yes | yes | authored interpreted policy and changed code | report 10 + actual combined test |
| Billing before follow-up | yes | no | none | none, despite passing integration |
| Billing after follow-up | yes | yes | policy-specific tests and report naming event 9 | report 11 + 9 local tests + operator combined test |
| Booking | no | no | none required | no fee work |
| Notifications | no | no | none required | no fee work |

Booking and Notifications module hashes and all coordination session state are byte-for-byte
unchanged across the fee stage. Their sole turns were the initial tasks. Billing's module
hash is also unchanged; its component tests changed. Delivery did not receive Billing's
later report in another model turn; pending work for idle sessions is intentional.

## Evidence and limits

[routing-rehearsal/](routing-rehearsal/) retains exact coordination state, pre-fee and
pre-Billing snapshots, operator actions, task timestamps/tool counts, final agent modules
and tests, and all three validation snapshots/results. Raw Codex profiles and credentials
remain local under ignored `runs/`; none are copied into Git.

The full repository suite passed **584 tests** against isolated FalkorDB; Ruff and diff
checks passed. Supersession is tested deterministically, not staged as an extra human
change in this live rehearsal. The live run used a single fee revision.

Delivery means the server emitted a response; it cannot prove transport receipt or human
attention. Read evidence comes from observed agent actions, not a read badge. Applied
reports are claims by trusted local agent labels, corroborated by specific tests, not
independent proof of every requirement. No authentication or semantic inspection prevents
an agent from mislabeling raw policy prose as a direct message. Explicit dependencies
must be correct. Current policy history is returned in full, suitable for this small demo,
not a measured large-project performance design. The Python combined test does not exercise
browser JavaScript or a deployed service. This is one real rehearsal, not a reliability rate.

Exact recording instructions: [recording-workflow.md](../recording-workflow.md).

## Recovery, reset and prepared recording

A controller crash/reconnect preserved the exact coordination state and existing terminals.
The first immediate restart exposed a preflight socket `TIME_WAIT` issue; setting
`SO_REUSEADDR` to match uvicorn fixed it. The recovered report matched all tested module
hashes. This was an operator controller restart, not an agent wakeup.

The operator then clicked Reset in the browser. All **62** archived source, test and
validation files matched their pre-reset SHA-256 hashes. The prior graph remained exactly
unchanged. `ARCHIVED` and the full report are retained in `runs/routing-rehearsal`.
See [reset-verification.json](routing-rehearsal/reset-verification.json).

Fresh recording: http://127.0.0.1:18939/ — all four real panels connected, all four
prepared starter prompts unsent, zero agent tasks started, zero coordination events.
Root: `/private/tmp/midflight-agent-communication/runs/interactive-6da9d6d5d2`.
Session: `midflight-2716e6af`. Screenshot: [recording-ready.png](routing-rehearsal/recording-ready.png).

For this prepared run, set:

```sh
cd /tmp/midflight-agent-communication
RUN=/private/tmp/midflight-agent-communication/runs/interactive-6da9d6d5d2
```

Follow the [recording sequence](../recording-workflow.md). The operator commands are:

```sh
.venv/bin/python -m midflight.communication.validate "$RUN" --label baseline --id-field id
# After the fee task and the one useful Billing follow-up have completed:
.venv/bin/python -m midflight.communication.validate "$RUN" --fee 400 --label fee --id-field id
```

Use `delivery_id` instead if that is the freshly published contract. The new agents have
not yet chosen their implementation. Do not promise a repeat of this rehearsal's choices
or timing, and do not report a passing test until it actually passes in the recording run.
