# Live interface-conflict rehearsals

These are fresh actual coding-agent sessions on FalkorDB, not replays of fabricated
claims. The visible prompts stayed “Add volume discounts.” and “Add promo codes.”
Pricing started first; Checkout started after Pricing's claim was approved.

## Deliberate fixture

Pricing's branch starts with get_promo_codes() returning dict[str, int]. Checkout's
branch starts with a caller-side prototype returning list[dict] records and a consumer
iterating those records. The business requirements do not fix that representation.
Agents declare their actual assumptions; the reviewer determines compatibility. No
bad claim, rejection, or automatic revision is injected. An agent can discover and
correct the drift before submitting, so no autonomous outcome is guaranteed.

## Reviewer

The isolated peer demo uses the local PigeonPost semantic review policy and hosted
Codex CLI inference transport. Application code validates findings and cited IDs.
Blocking findings get a second contradiction check and technical/product ruling.
Private mapping storage with a public list conversion is compatible; public mapping
output versus a caller expecting list records is not. Narrow review context includes
claim status and creation times, so earlier approved interfaces can be preserved.

Approved peer assumptions are shared; unapproved peer proposals cannot redirect the
already approved reference task. The demo preserves earlier approved claims when
settling a later technical disagreement. This adapter is scoped to the peer launcher.
An unavailable review does not count as approval. Inference latency can leave a review
pending; the agent must wait rather than implement the dependent work.

## Results (2026-10-17)

| Fresh run | Pricing | Checkout | Implementation integration |
| --- | --- | --- | --- |
| 1: run-1-b26449 | Approved rev 1 | Semantic mismatch → incomplete rev 2 → approved rev 3 | Passed |
| 2: run-2-640aec | Approved rev 1 | Pending when the 240-second trial budget ended | Not assessed |
| 3: run-3-ec996d | Approved rev 1 | Semantic mismatch → approved rev 2 | Passed |

Run 1 completed in 102 seconds. Its intermediate incomplete claim exposed misleading
partial-revision tool guidance. Peer instructions now require complete revisions to
match the local endpoint. Run 3 used the corrected guidance and completed in 103
seconds. Run 2 spent much longer before claim submission and hit the overall trial
limit while Checkout's AI review was pending; it is not counted as a successful run.

Successful runs combined the actual generated provider and consumer modules in a
fresh directory: the dictionary catalog returned SAVE10 = 10%, the ten-item volume
quote returned 10800 cents, and corrected promo checkout returned 9720 cents. Both
passed. In run 1 each agent used two check-ins; claim revisions used submit_claim.

Live reviewer controls, run before and after final policy changes, blocked the
explicit shape mismatch and accepted a provider converting its private dictionary
into the consumer's required public list. Those are backend controls, distinct from
the autonomous runs above. Full automated suite: 481 passed, 47 skipped.

Raw sessions, MCP replies, claim-state history, terminal transcripts, combined-code
integration output and runner scripts are retained locally under
~/.local/share/midflight-demo/interface-trials/.

## Manual demonstration

1. Press Enter in Pricing. Wait for APPROVED.
2. Press Enter in Checkout. Observe the real review, then any autonomous correction.
3. Start Reporting and Notifications when desired.
4. In any window, request: “Include a price expiry time, and reject checkout when the
   quote has expired.” Price-only contract changes target Pricing and Checkout.
5. Finished agents discover updates when the human next gives them work; no idle
   wake-ups or automatic turns are generated.

Reset archives the previous run and prepares four fresh sessions with editable,
unsent basic prompts. Source fixture drift and AI review remain enabled after Reset.
