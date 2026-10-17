# Delivery business demo

Run the four-peer terminal harness with:

```sh
uv run --extra falkordb --extra demo python -m midflight.theater.peers \
  --scenario delivery --port 8909 --api-port 8910
```

FalkorDB runs locally on port 6379. The hosted AI reviewer uses the installed Codex
CLI and saved sign-in; unavailable review remains pending rather than approving work.
No external email is sent, and no actual payments are collected.

## Ready prompts

- Billing: “Implement billing and revenue reporting.”
- Delivery: “Implement delivery management.”
- Booking: “Build the customer booking flow.”
- Notifications: “Implement customer notifications.”

Startup and Reset create fresh projects, graphs, identities, workspaces and sessions.
Each composer is prefilled but unsent. Press Enter in each pane to start work; agents
remain available afterward. Reset retains the previous run's files and evidence.
The original shop scenario remains available with --scenario shop.

## Application and interface drift

All workspaces contain a real standard-library Python HTTP app, module prototypes and
baseline tests. One credit is 100 integer cents. Delivery owns record creation,
lookup, cancellation and get_delivery_records(). Billing summarizes actual saved
charges/refunds. Booking displays server-provided amounts. Notifications generates
nonmonetary confirmation messages.

Billing's branch expects get_delivery_records() to return a flat list of records.
Delivery's prototype proposes a dictionary keyed by ID. Neither is fixed by business
policy. Agents declare their own assumptions; an AI review can identify their public
interface incompatibility, confirm it in a second check and propose a technical fix.
No bad claim, rejection or scripted correction is injected. An agent may learn the
approved peer expectation and adapt before submitting: that is a valid outcome too.

## Business change

Type this in any agent window:

> When a delivery is cancelled, keep a four-credit cancellation fee and refund the
> rest, never below zero.

The shared cancellation-policy requirement belongs to Billing and Delivery. Its
update leaves the delivery-record and booking-request schemas intact, so Booking and
Notifications receive no policy directive. Billing reports actual saved refunds;
Booking displays returned values rather than calculating policy. A four-credit fee
therefore means refund_cents = max(total_cents - 400, 0).

There are no idle wake-ups. If Delivery has already finished, ask it to continue work;
its next check-in discovers the directive without repeating the new rule. An agent
still working can discover it at its task/completion checkpoint. Updates travel via
Midflight, not direct messages between agents.

## Actual fresh-agent validation, 2026-10-17

Full four-agent run: delivery-trials/run-72b8b6b0.

- Billing's first claim was approved.
- Delivery read Billing's approved list expectation and aligned before submitting;
  its first claim was approved. This run did not produce a Delivery rejection.
- Booking received a real semantic_mismatch, revised its claim, and was approved.
- Notifications was approved without a revision.
- Independent integration of all four generated modules passed full-refund behavior,
  creation, idempotent cancellation, revenue aggregation, booking and confirmations.
- The exact business-change prompt above was submitted to Billing. Its agent published
  plan v2 through the generic plan tools. Only Billing and Delivery received plan-change
  directives, both acknowledged and approved at revision 2.
- Delivery was given only “Continue delivery management.” It discovered the fee rule
  through Midflight and implemented it.
- Delivery totals of 1200, 400, 300 and 0 cents refunded 800, 0, 0 and 0 cents. Billing
  reported 1100 cents retained. Booking and Notifications module hashes were unchanged.
- Independent real HTTP tests passed booking, cancellation, revenue, confirmation and
  customer HTML routes using the generated modules and shared app router.

Separate parallel pair: interface-trials/run-1-3f0d56.

- Billing and Delivery started back-to-back and both submitted while reviews were pending.
- AI review caught the genuine list-versus-dictionary semantic mismatch. Because neither
  was approved yet, the technical resolution led both claims through revision.
- Both corrected claims were approved, with informational shared-file notices.
- Actual combined Billing and Delivery modules passed creation, full refunds and revenue.
- This is evidence of real conflict detection, not a guaranteed “first approved, second
  rejected” ordering. Do not narrate an autonomous verdict before observing it.

All local terminal transcripts, session/MCP histories, reports, claim-state timelines,
runner scripts and independent integration outputs are preserved in the run directories
under ~/.local/share/midflight-demo/. Automated suite: 483 passed, 47 skipped.

## Visible review status

Each coding-pane header has a compact badge driven by saved claim state: NO CLAIM,
REVIEWING, APPROVED, NEEDS REVISION, INCOMPLETE CLAIM or HUMAN REVIEW. It is separate
from the raw terminal transcript and does not parse words in agent prose. Click it
to read the claim ID/revision, review explanation and proposed correction without
expanding tool JSON. Earlier saved revisions are shown as history after correction.
Approval means declared intent is approved; code/test completion is a separate check.
Status polling does not start agent turns or call check_in on their behalf.
