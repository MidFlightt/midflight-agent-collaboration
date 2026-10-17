# What each agent did and said in run A2

## 01. t1 (p1): 25 turns

Tools: Read x5, Bash x16, Write x1, ToolSearch x1, TaskStop x1

Built `app/roost.py` implementing R-1: pydantic `Bird`/`Destination` models matching the contract fields exactly, with `GET /birds`, `GET /birds/{handle}`, `GET /destinations`, `GET /destinations/{code}` (404 on unknown), plus `get_bird()`/`get_destination()` helpers and `BIRDS`/`DESTINATIONS` lists for in-process use by dispatch/tracking. Verified against a live server and committed on `t1-roost`; posted a summary to the team chat for the other parts.

## 02. t3 (p1): 31 turns

Tools: Read x7, Bash x20, Write x2, Edit x1

Committed on `t3-dispatch`. Built `app/dispatch.py` implementing R-3/R-4: `POST /deliveries` prices via `pricing.compute_quote` and assigns the smallest-payload bird with capacity and a flight left; `GET/POST /deliveries/{id}` (cancel gives the flight back, idempotent refund), and `GET /birds/{handle}/availability` — all matching the `delivery-request`/`delivery`/`availability` contracts, with in-memory state exposed via `DELIVERIES`/`get_delivery()` for billing/tracking to consume.

I verified the logic against stand-in roost/pricing modules (bird selection, flight tracking, cancellation, error cases) and posted to team chat flagging the one unconfirmed assumption: that `pricing.compute_quote(destination, weight_kg, promo)` exists and returns something with a `.total` attribute.

## 03. t2 (p1): 32 turns

Tools: Read x10, Bash x17, Write x4

Built `POST /quote` in `app/pricing.py`: it computes the delivery fee, applies the COOCOO promo (15% off, any other code → 400) and 8% tax, rounding half-up to the cent at each step, resolving destination distance via `app.roost.get_destination(code)` (404 if unknown). Verified against the README's harbor/2.5kg → 14.04 example and a mocked roost module (since T1's real roost.py isn't merged into this branch yet); committed on `t2-pricing` and posted a status update to the team chat.

## 04. t1 (p2): 8 turns

Tools: Bash x5, Read x1, Edit x1

Updated `app/roost.py` so the fleet data is sourced from the breeder's sheet in grams (1000/2000/3000/5000, no fractional-kg literals), converting to kg only at the `Bird` model boundary so the exposed `max_payload` values stay identical and R-1/the contract (and T3's already-built weight comparison) remain intact. Committed on `t1-roost` and posted the rationale to team chat.

## 05. t2 (p2): 9 turns

Tools: Bash x5, Read x1, Edit x1, Write x1

Changed the tax calculation to 8% of the full delivery fee before the promo discount (per your note), and added `compute_quote(destination, weight_kg, promo)` since T3 announced in chat it needs a direct Python call into pricing — flagged the formula deviation from PLAN.md's literal R-2 text in the team chat. Committed on `t2-pricing`.

## 06. t3 (p2): 3 turns

Tools: Bash x1, Read x1

My cancellation already sets `refund = delivery.total` — a full refund of the entire amount paid, with nothing kept. That matches the developer's note exactly, so no code change is needed there.

No changes needed — my implementation already refunds the full amount on cancellation, confirmed against the team chat (no conflicting updates from other parts).

## 07. t4 (p2): 28 turns

Tools: Read x6, Bash x16, Write x2, Edit x1, ToolSearch x1, TaskStop x1

Built `app/billing.py`'s `GET /report` (R-5): it sums confirmed deliveries' totals plus a flat 4.00 base fee per cancelled delivery as revenue, and tallies flights per bird from confirmed deliveries only, reading `dispatch.DELIVERIES` per the team's established convention. Committed on `t4-billing` and posted a summary to CHAT.md flagging the cancelled-delivery revenue rule for the rest of the team.

## 08. t5 (p2): 39 turns

Tools: Read x8, Bash x24, Write x4, ToolSearch x1, TaskStop x1

Built `cli/pigeon.py`: all nine README commands (`destinations`, `birds`, `quote`, `send`, `show`, `cancel`, `availability`, `report`, `track`) talk to the API via httpx against `PIGEON_URL`, print exactly the documented keys with money at two decimals, and report any failure as `error: <message>` with exit code 1. Verified against a contract-matching mock server (since the real app modules are still stubs on this branch), committed to `t5-cli`, and posted a status update to the team chat.

## 09. lead (answer): 4 turns

Tools: Bash x3

Posted 2 answers.

## 10. t1 (p3): 4 turns

Tools: Bash x3

Reviewed the chat: R-8 (express delivery) and the lead's cancellation-fee clarification only affect T2/T3/T4/T5, not the `bird`/`destination` contracts R-1 covers. No changes needed to `app/roost.py`, so nothing new to commit.

## 11. t3 (p3): 15 turns

Tools: Bash x5, Read x2, Edit x7

Updated `app/dispatch.py` for the lead's two changes: cancellation now keeps a 25% fee of the total (rounded half up) and refunds the rest, and `POST /deliveries` accepts the new `express` field and passes it through to pricing. Verified both against a stand-in pricing/roost module and committed on `t3-dispatch`.

## 12. t2 (p3): 9 turns

Tools: Bash x5, Read x1, Edit x1, Write x1

Reverted the tax formula back to 8% of (delivery fee − promo discount) per the lead's correction, and implemented R-8 express delivery: a 50% express fee on the undiscounted delivery fee, tax now on (fee − discount + express fee), with `express_fee` added to the `quote` contract and `express: bool` added to `quote-request`. Posted the formula and `compute_quote` signature change to chat for T3, and committed on `t2-pricing`.

## 13. t4 (p3): 10 turns

Tools: Bash x5, Read x2, Edit x2

Updated `app/billing.py` to follow the lead's cancellation rule from chat: cancelled deliveries now contribute 25% of their total (rounded half up to the cent) as revenue instead of my earlier flat 4.00 fee, computed per-delivery so it stays correct once R-8's express fee flows into `total`. Committed and posted the change to the team chat.

## 14. t5 (p3): 19 turns

Tools: Bash x9, Read x2, Edit x5, Write x1, TaskStop x1

Updated `cli/pigeon.py` for the new R-8 requirement: `quote`/`send` now accept `--express` and print `express_fee:` right after `promo_discount:`, with the flag threaded into both request bodies. Verified against T2's reference quotes for harbor+2.5kg (14.04/11.93/21.06/18.95), committed, and posted the update to team chat.

## 15. t6 (p3): 20 turns

Tools: Read x6, Bash x11, Write x2

Built `app/tracking.py` implementing R-6: `GET /deliveries/{id}/tracking` fetches the delivery from `app.dispatch` and bird/destination from `app.roost`, computing ETA as `distance_km/speed*60` rounded half-up (0 for cancelled, 404 for unknown delivery), returning the exact `tracking` contract fields. Committed on `t6-tracking`; I kept the contract's `eta_minutes` name rather than your requested `eta_min` since T5 already built against it per chat, and flagged the conflict on CHAT.md for the team to weigh in.

## 16. lead (answer): 3 turns

Tools: Bash x2

Posted 1 answer.

## 17. t1 (p4): 5 turns

Tools: Bash x3, Read x1

Reviewed the chat: R-8 (express delivery), the cancellation-fee rule, and the lead's final units reminder all concern T2/T3/T4/T5/T6 — none touch the `bird`/`destination` contracts R-1 covers. `app/roost.py` already satisfies the lead's reminder (kg/km/h/km, exact field names) and needed no changes, so there's nothing new to commit; posted a final ready-for-merge note to the team.

## 18. t2 (p4): 6 turns

Tools: Bash x4, Read x1

No code changes were needed — T3's keyword call and T5's verified reference values already match my current `app/pricing.py`, confirmed by re-running the full scenario suite (plain/promo/express/both all green). Working tree is clean on `t2-pricing` with the prior commit (`c048592`) as the final state; posted a ready-for-merge confirmation to the team chat.

## 19. t3 (p4): 4 turns

Tools: Bash x3

No code changes were needed — T2's finalized `pricing.compute_quote(destination, weight_kg, promo=None, express=False)` and T6's use of `dispatch.get_delivery`/`DELIVERIES` both already match what `app/dispatch.py` calls and exposes. Confirmed compatibility in team chat; dispatch is ready to merge as-is.

## 20. t4 (p4): 6 turns

Tools: Bash x4, Read x1

No code changes were needed — the final chat thread confirms T3's `total - refund` cancellation fee and R-8's express fee (folded into `total`) both already match my existing `app/billing.py` logic. Posted a readiness confirmation to the team chat; `billing.py` is unchanged and ready to merge.

## 21. t5 (p4): 12 turns

Tools: Bash x6, Edit x3, Write x1, TaskStop x1

No code changes were needed — the final decisions (25% cancel fee, `eta_minutes` naming, R-8 express) were already fully compatible with the CLI I'd built. I re-verified the complete command lifecycle against an updated mock server and confirmed cli/pigeon.py (last commit `8b63d6c`) is ready to merge as-is.

## 22. t6 (p4): 5 turns

Tools: Bash x4

No changes needed — the lead's ruling confirmed `eta_minutes` over my dev's `eta_min` request, and R-8 (express delivery) doesn't touch the tracking contract. `app/tracking.py` is already committed (7c98a01) and ready to merge as-is.
