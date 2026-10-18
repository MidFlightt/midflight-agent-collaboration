# Four-panel recording workflow

The controller starts four real Codex sessions. Each prompt is prepared but unsent.
There is no reviewer, model call inside MidFlight, approval gate or idle agent wakeup.
The operator starts useful tasks and runs combined-code validation explicitly.

## Communication semantics

- A topic update without `to` uses the complete current dependency graph audience.
  `topic` with `to` is rejected, even if the explicit list is a subset of subscribers.
- A direct message omits `topic` and supplies `to`. It is peer conversation, not a
  publication that changes shared requirements. Agents must publish interpreted policy
  on its affected topic; the server cannot detect a policy disguised as direct prose.
- `object` records exact interface/policy problems with affected requirements and an optional
  alternative. Only its author resolves with `send(kind="resolve", reply_to=objection_id,
  body="How it was addressed")`. Historical proposals remain data, not active workflow.
- Replies inherit their parent's topic and audience plus current subscribers. They cannot
  relabel a topic or override its recipients. A new publication linked to a private message
  still uses the full graph audience. Interface ownership and version checks remain intact.
- Latest policy revision per topic is actionable. `policy_history` retains all visible
  revisions, `superseded_by`, exact `applied_report_ids` and per-session delivery metadata.
  A superseded revision is not silently read or applied. Applying an old ID never clears
  the current revision. Session cursors, delivery records and retry receipts are durable.

## Evidence vocabulary

**Routed** means the durable event names an agent as recipient. **Delivered** means a
server response includes it (`delivered_policy_ids` records policy bodies returned,
including context outside the paginated event stream). Transport loss is possible; this
is not proof the model read it. **Read** requires observable agent behavior referring to
that exact change. **Applied** is an agent-authored report referencing the exact policy
ID, corroborated separately by code/test evidence. It is still a report, not an approval.

A passing combined test alone proves neither reading nor application by Billing.
An idle recipient stays pending until its next useful task. Never wake it just to
clear a queue, repeatedly nudge it, or run automatic check-ins.

## Recording sequence

1. Open the prepared four-panel run and submit each of the four prepared prompts once.
   This simultaneous start was used in the object-tool rehearsal. Let agents discuss
   or adapt to published boundaries; do not force an objection or script dialogue.
2. Let all four turns finish. The starters intentionally disagree: Billing's local
   prototype returns a list, Delivery's returns an ID-keyed mapping. Consumers must
   use the published owner boundary when it satisfies their requirements, or raise a
   concrete objection. Local peer files remain starter snapshots. Report any open
   incompatibility beside integration results; a pass never resolves it.
3. The operator runs (from this repository, substituting the current run root):

   `.venv/bin/python -m midflight.communication.validate RUN --label baseline --id-field id`

   Use the actual published ID field (`id` or `delivery_id`). This copies each agent's
   owned module unchanged, executes their local component suites separately, and imports
   all four actual modules in a fresh subprocess. Results explicitly say `executed_by:
   operator`. A failure in either component or combined tests fails the CLI. The report
   indicates when current module hashes differ from the saved validation.
4. In Delivery, submit: “When a delivery is cancelled, keep a four-credit cancellation
   fee and refund the rest, never below zero.” Let that useful turn finish. Inspect
   routed recipients and per-session delivery evidence; Billing may still be idle.
5. Give Billing exactly one useful follow-up task: “Add regression coverage for revenue
   reporting across mixed confirmed and cancelled deliveries under the current shared
   requirements, including small totals and previously saved refunds.” Record that
   operator action. Let Billing consume current context and report its own work.
6. Operator runs:

   `.venv/bin/python -m midflight.communication.validate RUN --fee 400 --label fee --id-field id`

   Compare Booking/Notifications code and session state with the pre-fee snapshot.
   Inspect exact policy application reports independently from this test result.
7. Reset archives the old report, graph, code, tests, validation and operator evidence;
   it closes that run's terminals and creates a fresh graph and four unsent prompts.
   Do not start the new prompts until recording is ready.

Use a new validation label for every invocation; evidence is never overwritten in its
validation directory. `integration.json` points to the latest result, with earlier results
retained. There is no claim that mocked local tests are end-to-end validation. The combined
suite exercises Python calls, not browser JavaScript or a production deployment. Agent
choices and timings vary; failed runs must remain in the evidence.
