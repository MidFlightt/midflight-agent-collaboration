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
Delivery's branch has an ID-keyed provider and an existing mapping-based Billing
caller. Both branches work with their own callers and baseline tests; composing
Billing's list caller with Delivery's mapping provider fails on nonempty records.
This branch drift is the real incompatibility for the AI reviewer to resolve. The
basic prompts do not specify a return shape or tell an agent to disagree.
Neither return shape is fixed by business policy. Agents declare their own assumptions; an AI review can identify their public
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

## Review results in the terminal

MidFlight's MCP response starts with the saved claim verdict, findings and suggested
correction, followed by the next step and contract reference. Both local and hosted
MCP use the same renderer. Approval covers declared intent, not implementation tests.
There are no external claim badges or ready labels. Agent commentary is generated
by the coding agent; it is not the source of the verdict. The coding client controls
whether a tool response is collapsed; expand tool details to read the full review.

The complete claim response also ends with a short receipt generated from the same
saved verdict. This keeps the verdict visible in clients that preview the tail of
collapsed tool results. Rejections include the first blocking reason and correction;
all findings and directives remain in the full result. No agent narration is required.

Validated with a fresh real Codex CLI Billing session on October 17: its collapsed
submit_claim output displayed `Claim C-1 rev 1: APPROVED` and the code-verification
limit, matching the saved FalkorDB claim. The original user session was preserved.
Evidence: local run `~/.local/share/midflight-demo/peers-3647e35d29/`, including
`native-reply-validation.json` and `billing-native-reply-transcript.txt`. Rejection
receipts are covered by automated renderer tests; this check did not produce a fresh
autonomous rejection. Full suite: 488 passed, 47 skipped.

## Multiple terminal viewers

All viewers attach to one tmux window, so the coding panes share one size. Background
or unfocused viewers must not resize it. The foreground viewer restores its size on
focus or a click; a ResizeObserver also handles container changes. New tmux viewers
use ignore-size so attaching a small background viewer cannot implicitly shrink the
window. This changes terminal geometry only, preserving processes and prompt input.

Validated on the existing live session with both Chrome (204 columns) and the narrow
in-app viewer (95 columns): clicking each viewer transferred sizing, and returning to
Chrome restored all four full-width panes without resetting agents. Automated sizing
checks cover focus, hidden tabs, zero-size containers and coalesced resize events.

## Coherent branch setup: three fresh real-agent runs

The earlier setup gave Delivery Billing's list-based caller, making early adaptation
an obvious choice. Delivery now starts with its own mapping-based caller and baseline
test. Each branch is coherent on its own; integrating the unchanged branches fails
with a TypeError for a nonempty delivery. This models independently evolved branches.
The generic repository rule is to preserve existing callers and coordinate interface
changes. No prompt asks agents to disagree; no verdicts or claims are injected.

Three independent fresh Codex CLI pairs, same basic prompts, starting Delivery after
Billing's first approval:

| Run | Billing first claim | Delivery first claim | Delivery corrected claim | Generated-module integration |
| --- | --- | --- | --- | --- |
| run-1-6c273e | APPROVED r1 | NEEDS_REVISION r1 | APPROVED r2 | Passed |
| run-2-37080d | APPROVED r1 | NEEDS_REVISION r1 | APPROVED r2 | Passed |
| run-3-0ab85d | APPROVED r1 | NEEDS_REVISION r1 | APPROVED r2 | Passed |

In all three, the hosted AI reviewer identified the actual list-versus-ID-keyed-map
boundary conflict and required Delivery to preserve Billing's approved list interface.
Billing remained approved. The actual generated Billing and Delivery modules were
combined and exercised with creation, saved revenue, full refunds and post-refund
revenue. Local evidence, original sessions, timelines, first revisions and terminal
transcripts are in ~/.local/share/midflight-demo/coherent-branch-trials/. The repeat
runner is rehearse.py, with summary.json and one trial-results.json per run.

For this demonstration, send Billing first; once its tool result says APPROVED, send
Delivery. Sending both while their reviews are pending can require both to revise.
Three successes demonstrate repeatability for this setup, not a deterministic promise
about every future model run. Do not hide an early adaptation if one occurs.

Automated suite after this fixture change: 489 passed, 47 skipped. The cancellation
policy test still verifies that only Billing and Delivery receive its update.

## Bounded review waits and controller recovery

The parallel-review experiment was reverted. The live controller had not loaded that
change; a stalled inference call and the serial durable job queue were observed in
the slow run. Earlier single-request benchmark gains did not establish live end-to-end
performance. Keep independent confirmation and correction selection serial for now.

The hosted reviewer now limits each CLI call to 20 seconds and shares a 30-second
budget across detection, confirmation and correction within one review attempt.
The claims service can retry an unavailable attempt once, so this is not a 30-second
end-to-end SLA; queued jobs and agent thinking add time. Infrastructure failures at
any review stage leave the review incomplete; they cannot become approval through a
secondary-check fallback. The entire CLI process group is killed and reaped after a
call, including the Node wrapper's native child. Raw CLI diagnostics remain private.

Live hosted-model controls using recorded real claims: the restored serial bounded
review caught the mapping/list conflict in 19.084 seconds and accepted the aligned
list claim in 3.442 seconds. Evidence is in
~/.local/share/midflight-demo/review-latency/bounded-serial-controls.json. This is a
review replay, not a new autonomous four-agent run or a guaranteed response time.

A controller can now resume a delivery run with:

```sh
python -m midflight.theater.resume /absolute/path/to/existing/run
```

Stop the previous controller/worker first: there must never be two workers against
the same graph. Resume reads interactive.json, the saved report and the existing
private agent launch configuration. It validates the original identities and ports,
reuses the graph, plan, claims, durable jobs, workspaces and tmux sessions, and starts
no new coding agents. It does not seed/reset the project or extend credentials.
Tests verify preservation and identity/port refusal, the shared time budget, failure
gating, and cleanup of a real wrapper/child process on timeout.
