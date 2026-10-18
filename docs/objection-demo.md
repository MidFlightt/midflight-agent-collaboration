# Existing-interface objection demo

Run `uv run --extra falkordb --extra demo python -m midflight.communication.objection_demo --port 18942` with the local FalkorDB running. This is a separate scenario; the regular delivery demo is unchanged.

## Establish the baseline

The Delivery workspace contains a working active-only listing, creation, individual lookup and idempotent cancellation. Cancelled records remain stored. There is no accounting enumeration API yet. This is an existing implementation choice, not a human prohibition on adding an API.

Send the prepared Delivery prompt once: review and publish the existing API without changing its implementation. The real Delivery agent authors the publication. Wait for that turn to finish, then prepare its next normal work prompt:

> Improve delivery validation and tests. Address relevant peer updates.

The Billing prompt is already prepared:

> Implement billing and revenue reporting, including cancelled deliveries and their recorded refunds.

## Exercise the objection

1. Start Billing against the published baseline.
2. Once Billing records an objection, start Delivery's prepared work turn. No human solution or requirement change is needed.
3. Delivery can extend the API and preserve the active-only customer-facing default. Billing receives relevant updates at work checkpoints and may adapt and resolve its own objection.

There are no idle wakes, polling model turns, injected objections or waiting barriers. If Billing finishes before the revised interface arrives, it will need another ordinary work turn. A final check-in only delivers changes that already exist. Agent timing and reasoning remain variable; the test does not guarantee identical transcripts on every run.

Keep Booking and Notifications unsent for this two-agent test. The delivery-record topic includes Booking as a subscriber, but excludes Notifications. Reporting a resolution is not independent integration evidence.

## Observed real-agent trial

A retained local trial on 2026-10-17 used the actual Codex CLI sessions and FalkorDB:

- Delivery published existing interface #1 revision 1 without changing baseline code.
- Billing recorded objection #2 and question #3: the active-only enumeration cannot supply cancelled records.
- Delivery's next normal work turn published interface #4 revision 2, adding `get_delivery_records(*, include_cancelled=False)`.
- Billing used `include_cancelled=True`, reported its code change and resolved objection #2 itself in event #6.
- Delivery implemented the additive option and retained the active-only default. No human solution prompt was sent.
- A fresh subprocess imported the actual two generated modules unchanged. Checks passed for empty reporting, active-only default, all-record accounting, cancelled counts, recorded refunds, repeated cancellation, snapshot isolation, historical partial refunds and invalid IDs. Notifications was outside the objection audience.

Machine-local evidence, transcripts and exact module hashes are retained under the ignored `runs/objection-validated-trial-20261017-235732/` directory. Raw sessions and credentials are not committed.

Reset preserves the previous run and creates new workspaces with the baseline publication prompt. Establish the baseline again before starting Billing.

## Two-prompt overlapping work mode

Run the same module with `--overlap` to prepare Delivery's implementation task and
Billing's reporting task unsent. Start Delivery, then start Billing as soon as its
interface is published, while Delivery is still implementing/testing. A final
check-in and updates returned by send may reveal Billing's objection during that
same work turn. There is no publication-only setup turn or third prompt in this
mode, and no idle wakes, delays or synchronization barriers. Reset retains the
selected mode. This is timing-dependent: Delivery can anticipate a compatible
extension, or finish before an objection arrives. The validated staged trial
above does not establish repeatability for this overlapping variant.

The terminal viewer masks the exact Codex “Heads up” weekly-quota banner for recordings, including wrapped notices. The underlying terminal stream and saved transcripts retain it; model output and other errors are not filtered. The compact quota indicator remains visible. This display mask works independently of the Highlights toggle.
