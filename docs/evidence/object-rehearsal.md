# Four-tool objection workflow: implementation and real rehearsal

This extends `2ef022f` on `codex/agent-communication`, without restarting the migration.
The previous prepared run on port 18939 was preserved throughout implementation and
validation. Earlier source, evidence and graphs remain intact. Changes are confined to
`MidFlightt/midflight-agent-collaboration`; original Midflight and official repositories
are unchanged.

## Changes

The active MCP tools are exactly `join`, `send`, `check_in`, `object`.
`agree`, proposal creation, participants/acceptances and send-based objection creation
are removed from the active API. Historical records and retry receipts remain readable,
without promotion to current defaults or actionable proposals. Legacy objections remain
visible and author-resolvable; missing historical fields are not invented.

`object` takes publication ID, exact revision, problem, affected requirement/dependency,
retry ID and an optional alternative. It returns a stable objection ID. Routing reaches
the publisher, original publication audience, current graph subscribers and interface
owner if applicable. It cannot target unrelated agents or challenge an invisible publication.
The affected requirement is an agent-authored reference, not a server-verified claim.

Only the objection author resolves via `send(kind="resolve", reply_to=objection_id,
body="How addressed")`. Publication, supersession, ownership transfer, tests and silence
do not resolve it. Ownership and publication versions remain independent. There is no
veto, approval gate or mandatory acknowledgement. Agents continue unaffected work and
escalate unresolved requirement conflicts to the human. MidFlight makes no model calls.

Integration results now include open objections at validation time. Live reports also
show current open objections beside saved results. Passing tests never remove them or
certify all compatibility. Topic routing, policy supersession, delivery metadata,
independent cursors, restart recovery and operator test attribution remain in place.

## Tests

**590 repository tests passed** with isolated FalkorDB; the focused communication suite
passed **40 tests**. Ruff and diff checks passed. Coverage includes interface and policy
objections, exact revisions, optional alternatives, author-only resolution, duplicate
requests, concurrent publication and objection retries, supersession, database and MCP
restart recovery, independent sessions, legacy records, and passing results retaining
open objections without advancing agent cursors.

## Observed rehearsal

All four short task prompts were submitted together, without scripted dialogue.
Billing's starter expected a list and Delivery's starter provided an ID-keyed mapping.
Billing stated its expectation in event 5, then received Delivery's publication (event 3,
revision 1) and explicitly adapted in event 9. Booking asked for the boundary, received
it in the same natural exchange, and used the published response fields.

**No formal objections occurred.** Direct adaptation satisfied these requirements; we
did not force an objection or claim a successful objection/resolution negotiation.
The object lifecycle is exercised by focused tests, not by a live dispute in this run.

| Measurement | Observed |
| --- | --- |
| Initial turns: Billing / Delivery / Booking / Notifications | 35.6 / 38.1 / 61.6 / 28.9 seconds |
| Delivery fee turn / Billing useful follow-up | 14.6 / 17.5 seconds |
| Explicit check_in calls across all turns | Billing 1, Booking 1, Delivery 0, Notifications 0 |
| Baseline component tests | 21 passed |
| Baseline actual combined-code test | passed, operator executed |
| Fee with Billing still idle | combined test passed; not consumption evidence |
| After Billing follow-up | 23 component tests + actual combined test passed |
| Coordination events / formal objections | 16 / 0 |
| Automatic wakeups / repeated nudges | 0 / 0 |

Delivery independently published initial full-refund policy 4 (revision 1). The fee
became policy 14 (revision 2), superseding it without changing the API. Delivery first
attempted the write with a stale expected revision; the service rejected it and the
agent corrected the version. This was one rejected write, not an extra policy event.

The fee source was sent only to Delivery. Policy 14 and its application reports routed
only to Billing and Delivery. Before Billing's follow-up, its cursor remained at 11
and its delivered policy IDs contained only initial policy 4. A combined-code pass at
that point did not prove Billing had consumed revision 2.

The operator then sent exactly one useful Billing task: “Add regression coverage for
revenue reporting across mixed confirmed and cancelled deliveries under the current
shared requirements, including small totals and previously saved refunds.” The exact
operator action and timestamps are retained. Billing checked in, added two tests and
reported application in event 16, explicitly naming policy 14 revision 2. Its production
module was unchanged because it already uses actual saved refunds. Its tests use mocks;
the operator separately tested the actual four assembled modules.

| Agent/state | Fee routed | Server-delivered | Read evidence | Applied evidence |
| --- | --- | --- | --- | --- |
| Delivery | yes | yes | interpreted source and changed refund calculation | report 15 + operator combined test |
| Billing before follow-up | yes | no | none | none |
| Billing after follow-up | yes | yes | policy-specific tests and report naming exact revision | report 16 + tests |
| Booking | no | no | none needed | no fee work |
| Notifications | no | no | none needed | no fee work |

Booking and Notifications module hashes and all coordination session state remained
unchanged across the fee stage. No additional turn was submitted to either. Delivery
remains idle after its own work; the later Billing report need not be consumed immediately.

## Evidence and limits

[object-rehearsal/](object-rehearsal/) contains the exact modules/tests, three validation
snapshots, coordination state, pre-fee/pre-Billing snapshots, task timestamps, call counts
and operator actions. Credentials and raw Codex logs remain only in ignored local runs.

This is one real rehearsal, not a reliability estimate. The combined test exercises
Python modules; it is not a production or end-to-end browser test. Delivery means the
server emitted a body, not guaranteed transport receipt or comprehension. Read evidence
comes from agent behavior; application reports are self-reports corroborated by limited
tests. Silence never implies receipt, agreement, application or verified compatibility.
Agent names are trusted labels. MidFlight cannot verify the truth of an objection or
stop policy prose deliberately mislabeled as a direct message. Correct subscriptions
and sensible requirement interpretation still depend on coding agents. Policy history
is returned in full; large-project performance was not measured.

[Exact recording steps](../recording-workflow.md): start all four prepared prompts,
validate actual combined code, introduce the fee through Delivery, give Billing the one
useful follow-up, then validate again. Inspect objection and consumption evidence
separately from test results. Never stage an objection for the recording.

## Archived rehearsal and fresh recording

After all validation completed, the browser Reset archived `runs/object-rehearsal`.
All **62** checked source/test/validation files retained their exact hashes, and the old
graph was unchanged. The earlier prepared run was not reset during this work.
[Reset verification](object-rehearsal/reset-verification.json) records the checks.

Fresh page: http://127.0.0.1:18940/ . All four panels are connected with **join, send,
check_in, object** configured. All prepared prompts remain unsent; zero tasks and zero
coordination events. [Ready screenshot](object-rehearsal/recording-ready.png).

Root: `/private/tmp/midflight-agent-communication/runs/interactive-6f7489fd08`.
Session: `midflight-fe517bca`.

For this run:

```sh
cd /tmp/midflight-agent-communication
RUN=/private/tmp/midflight-agent-communication/runs/interactive-6f7489fd08
```

1. Submit each prepared task once and let the four agents finish. Do not force objections.
2. Inspect any open incompatibilities and run the operator's actual-module test:

   `.venv/bin/python -m midflight.communication.validate "$RUN" --label baseline --id-field id`

3. Send Delivery: “When a delivery is cancelled, keep a four-credit cancellation fee and
   refund the rest, never below zero.” Let it finish. Inspect routing and delivery metadata.
4. Give Billing one useful task: “Add regression coverage for revenue reporting across
   mixed confirmed and cancelled deliveries under the current shared requirements,
   including small totals and previously saved refunds.” Record this operator action.
5. When Billing finishes, inspect its exact policy report separately and run:

   `.venv/bin/python -m midflight.communication.validate "$RUN" --fee 400 --label fee --id-field id`

Use `delivery_id` instead of `id` if the new publication chooses that field. Agent choices
and durations can vary. If an actual incompatibility remains open, retain and report it
alongside test results, discuss alternatives or escalate; do not mark it resolved merely
to finish a recording. Validation labels must be unique to retain prior attempts.
