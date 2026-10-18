# Owner-publication rehearsal — 2026-10-17

The follow-up replaces routine mutual acceptance with owner-published interfaces.
Two real four-terminal rehearsals were retained. No idle peer was notified or woken
for the fee change in either run. Delivery was started first; consumers were started
after its first interface publication to test use of existing shared context.

## Corrected run: published-interfaces-02

Delivery published an ID-keyed record interface. Billing followed it while keeping
compatibility with its local list callers. Booking consumed the published response
shape. Notifications published its own confirmation interface. There were **zero
proposals, zero agree calls and zero objections**; the initial mismatch was resolved
by following the provider's default rather than by an approval handshake.

All **22 component tests** and the independent combined-code workflow passed before
the fee change. After the change, **23 component tests** and the combined-code workflow
passed. The validator assembled actual owned modules, not the peers' local stubs.
Agent-local integration tests still used mocks; their results alone are not proof
of cross-component compatibility.

The human fee instruction was sent only to Delivery. Event 9 is the resulting policy;
event 10 is Delivery's application report. Both address only Billing and Delivery.
No interface revision was published: the API shape and calling conventions remained
unchanged. Booking and Notifications received no fee messages and had no further turns.

**Billing was deliberately left idle. Its policy is unread and unapplied.** Its
cursor and delivered-interface metadata did not advance. Billing's existing saved-refund
calculation worked with Delivery's changed code in the independent combined test, but
this does not mean Billing read, interpreted, applied or verified the new policy.
Billing, Booking and Notifications production-module hashes are unchanged.

| Agent | Initial turn seconds | Fee turn seconds | Explicit check_in calls, all stages |
| --- | ---: | ---: | ---: |
| Billing | 36.000 | no turn | 1 |
| Delivery | 34.526 | 15.529 | 2 |
| Booking | 59.788 | no turn | 1 |
| Notifications | 30.586 | no turn | 0 |

`join` and `send` also return updates, so zero explicit check-ins does not imply no
coordination context. Times are CLI task timestamps, not a controlled performance
comparison. Counts are requested calls extracted from CLI tool-call source. The CLI
used its configured default model, displayed as GPT-6.1-Sol. Operator actions were
initial task submission, the single Delivery fee instruction, and independent tests;
there was no notification, repeated prompt or agent polling loop.

Data: [coordination](published-interfaces-02/coordination.json),
[measurements](published-interfaces-02/measurements.json),
[idle verification](published-interfaces-02/idle-verification.json),
[operator actions](published-interfaces-02/operator-actions.jsonl),
[baseline test output](published-interfaces-02/baseline/result.json),
[fee test output](published-interfaces-02/fee-idle/result.json).

## First run: published-interfaces-01

Owner publication and idle delivery also worked in the first run, and its combined
code passed. However, Delivery included the initial refund formula in the interface
body. It then republished the interface for the fee change, unnecessarily queuing an
update to Booking. Booking stayed idle and did not change code, but the queued update
was unnecessary. This evidence is retained; it is not counted as successful isolation.

The instructions now separate stable API shape/calling conventions from changeable
business rules. The corrected run above kept the interface unchanged. This is an
agent-authored classification, not semantic enforcement by MidFlight. If an agent
puts unrelated business rules into a contract again, the service cannot recognize
that from free text without additional structure or interpretation.

## Coverage and limits

The full suite passed **571 tests in 15.36s** with real FalkorDB enabled. Coverage is:
**550 inherited tests, 8 tests from the first communication migration, and 12 tests
added for owner publication** (11 service/storage tests and one real stdio test),
plus **one validator exit-status regression test**.
Ruff and diff-whitespace checks also passed. The added tests cover owner/default
publication, competing declarations, CAS revisions, late subscribers, independent
session delivery, objections, optional agreement, transfer and database crash recovery.

The real rehearsal demonstrates normal publication and selective policy delivery;
it does not exercise a real-agent unresolved dispute, ownership handoff or response-shape
migration. Ownership handoff, objection state and revision delivery are covered by automated
behavior tests; a real code migration to a new response shape was not exercised.
The initial tasks were deliberately staggered; no speedup or token saving is established.

An idle peer needs its next useful task to receive pending work. There is no automatic
wake, eventual-completion deadline, reviewer gate or silent acceptance. Content correctness,
policy interpretation and adoption remain agent responsibilities. Owners are trusted local
labels, storage uses a whole-project CAS snapshot, and test assembly remains an operator
command rather than an automatic agent workflow.

The interrupted chat stopped the HTTP controller. The existing tmux sessions and graph
were inspected and retained; `--resume` reconnected the controller without restarting
agents, changing cursors, resetting the demo or submitting any prompt. Billing was still
unread/unapplied after recovery. Earlier reset evidence remains valid; no extra reset was
performed because of the review handoff.

The validator CLI also now returns failure if any component suite fails even when the
combined test passes. A dedicated regression test covers that prior false-success path.
The saved rehearsal results already had all component and combined return codes zero;
this correction did not require rerunning or waking the coding sessions.

Other review observations remain outside this follow-up: explicit direct-message
recipients can differ from a tagged topic's subscribers, explicit policy recipients
can be a subset of subscribers, and older policy revisions can remain in the outstanding
policy list until reported applied. This work does not claim coherent delivery semantics
for every message kind or complete supersession handling. The measured fee publication
used the default graph route and only one changed policy revision. Those broader routing
and policy-lifecycle decisions need their own scoped change and tests.
