# Natural discount-prompt trials

Four fresh local trials on 2026-10-17 used the actual Codex agents, FalkorDB-backed
Midflight service, and existing rule-based reviewer. No verdicts or incompatible
claims were injected. Pricing and Checkout started concurrently from these prompts:

- Pricing: “Add volume discounts.”
- Checkout: “Add promo codes.”

Each trial had fresh workspaces, plan, graph, tokens, claims and sessions. Reporting
and Notifications remained unstarted. The controller did not wake idle agents.

| Trial | Pricing | Checkout | Findings | Check-ins (Pricing / Checkout) |
| --- | --- | --- | --- | --- |
| 1 | Approved, revision 1 | Approved, revision 1 | None | 2 / 2 |
| 2 | Approved, revision 1 | Asked which codes/discounts; no claim | None | 2 / 1 |
| 3 | Approved, revision 1 | Approved, revision 1 | None | 2 / 2 |
| 4 | Approved, revision 1 | Approved, revision 1 | None | 2 / 2 |

Trials 1–3 specified promo-code support without a promo catalog. In trial 2 the agent
correctly asked for product details. Trial 4 added the normal product catalog entry
SAVE10 = 10% off to the shared requirements and README. The visible prompts stayed
the same. That is the setup now left ready for the human.

There were seven submitted claims, all approved on their first revision, no blocking
findings, no stale-plan retries, and no plan updates. These trials did not find the
requested natural approval/revision sequence. They are not evidence that semantic
review can catch conflicting discount policies: the local rule-only reviewer checks
structural contracts, ownership, references and related rules. File overlap is
informational, not by itself a blocking conflict.

Independent integration checks combined the actual generated Pricing and Checkout
modules for trials 1, 3 and 4. A ten-item quote at 1200 cents produced 10800 cents,
and SAVE10 produced a final order total of 9720 cents. All passed. This demonstrates
compatible discount composition for that input, not a comprehensive discount policy
or code verification by the claim reviewer.

Full local transcripts, session tool histories, reports, summary.json and combined
integration results are retained under ~/.local/share/midflight-demo/discount-trials/.
Run directories: run-1-60c959, run-2-02b0d7, run-3-f721f4, run-4-47ff44.
The temporary trial runner is retained there as trial-runner.py.

The next manual direction remains:

> Include a price expiry time, and reject checkout when the quote has expired.

A change to the price contract alone routes to Pricing and Checkout. That routing
has a separate real-FalkorDB proof and regression test. It was not simulated as a
successful agent adaptation in these discount trials. Idle agents discover it on
their next human-requested turn, as agreed.
