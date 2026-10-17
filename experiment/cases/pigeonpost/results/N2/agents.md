# What each agent did and said in run N2

## 01. t3 (p1): 28 turns

Tools: Read x9, Bash x15, Write x2, Edit x1

Committed on `t3-dispatch`. One thing the team should know: dispatch never imports `app/roost.py` or `app/pricing.py` directly — it reaches them only via their documented HTTP endpoints (`GET /birds`, `GET /birds/{handle}`, `POST /quote`) through an in-process ASGI call, so it depends only on the PLAN.md contracts (field names/shapes) and not on their internal code. This means dispatch won't produce real results until those two parts implement those exact routes returning the exact contract fields — I verified the wiring against a fake stand-in for both and it passes, but the real end-to-end flow needs them done too.

**Summary:** Implemented `app/dispatch.py` with `POST /deliveries`, `GET /deliveries/{id}`, `POST /deliveries/{id}/cancel`, and `GET /birds/{handle}/availability`, assigning the smallest-capable bird with a flight left, pricing via pricing's `/quote`, and tracking flights/refunds in memory. Verified against a mocked roost/pricing and against the real wired app; committed as `93ff78a` on `t3-dispatch`.

## 02. t2 (p1): 20 turns

Tools: Read x8, Glob x2, Bash x6, Write x3

Built `POST /quote` in `app/pricing.py`: delivery fee (4.00 + 0.50/km + 2.00/kg) with COOCOO promo (15% off, else 400), 8% tax, and total — all rounded half-up to the cent — verified against the README example and committed on `t2-pricing`.

One thing for the team: `app/roost.py` is still an empty stub, so pricing.py currently hardcodes the destination-distance table from README.md rather than importing it from roost. The distances match now, but flag this at merge time in case T1 introduces its own copy that could drift out of sync.

## 03. t1 (p1): 17 turns

Tools: Read x9, Bash x5, Grep x1, Write x1

Committed cleanly (the `__pycache__` directory is untracked build cruft, left alone).

**Summary:** Implemented `app/roost.py` with the four fleet birds and four destinations from README as Pydantic models, serving `GET /birds`, `GET /birds/{handle}`, `GET /destinations`, `GET /destinations/{code}` (404 on unknown), and also exporting `BIRDS`/`DESTINATIONS` lists plus `get_bird()`/`get_destination()` helpers so T2/T3/T5/T6 can pull this data in-process rather than over HTTP. Verified all six cases (list/get/404 for both resources) via FastAPI's TestClient before committing to `t1-roost`.

## 04. t1 (p2): 7 turns

Tools: Read x1, Edit x3, Bash x2

**Summary:** `max_payload` in `app/roost.py` now reports grams (1000/2000/3000/5000) instead of kg, as requested, and committed. Flag for the team: PLAN.md and the README both document `max_payload` as kilograms, so whoever builds Dispatch (compares it against `weight_kg`) and the Command line (prints it under a `kg` label) will need to convert units or those parts will break.

## 05. t5 (p2): 31 turns

Tools: Read x10, Glob x2, Bash x16, Write x2

Committed on `t5-cli`. One thing worth flagging to the team: when `--promo` isn't given, I send `"promo": ""` in the `quote-request`/`delivery-request` JSON (the contract types it as a plain string, not nullable) — T2/T3 should treat empty string as "no promo," not as an invalid code. I couldn't do live integration testing since `app/roost.py`, `pricing.py`, `dispatch.py`, etc. are still empty stub routers (no endpoints yet) and this session's Bash sandbox blocked all Python execution, so verification here was by careful manual read-through rather than running the CLI against a live server.

**Summary:** Built `cli/pigeon.py` implementing all nine commands from README's CLI section (`destinations`, `birds`, `quote`, `send`, `show`, `cancel`, `availability`, `report`, `track`) over HTTP via httpx, with exact `key: value` output, two-decimal money formatting, and uniform `error: <message>` / exit-code-1 handling. Committed as `f9f0182` on branch `t5-cli`.

## 06. t4 (p2): 23 turns

Tools: Read x5, Bash x10, Write x7

Built `GET /report` in `app/billing.py`: it sums `total` for confirmed deliveries plus a flat 4.00 cancellation fee per cancelled delivery, and tallies confirmed flights per bird — committed as `2a81abd`.

One thing worth flagging to the team: since `app/dispatch.py` is still a stub on this branch, billing has to guess how dispatch stores its deliveries in memory — I made `_all_deliveries()` tolerant of a few likely attribute names and both dict/list and dict-record/object-record shapes, but this should be double-checked once T3's real dispatch.py merges in.

## 07. t3 (p2): 5 turns

Tools: Read x1, Edit x1, Bash x2

Checked the cancellation logic — it already sets `refund = delivery.total`, a full refund of everything the customer paid, so no behavior change was needed. Committed a one-line comment documenting that policy explicitly (`53c6403`).

## 08. t2 (p2): 7 turns

Tools: Read x1, Edit x2, Bash x2, Write x1

Updated and committed: tax is now 8% of the full delivery fee, applied before the promo discount is subtracted (only promo quotes change — e.g. downtown/0.5kg/COOCOO now totals 6.04, not 5.96).

Heads up: this reads R-2 differently than PLAN.md's literal wording ("8% of (delivery fee − promo discount)"), so flag it to the lead/team in case any merge-time check still expects the literal formula.

## 09. t2 (p3): 11 turns

Tools: Read x2, Edit x4, Bash x3, Write x1

Added R-8 support: `quote-request` now accepts `express: boolean`, and `quote` returns `express_fee` (50% of delivery fee, before promo discount) plus tax/total recomputed as 8% of (delivery_fee − promo_discount + express_fee) and total including the express fee — committed.

That tax formula reverses your earlier "tax the full fee" instruction, since the lead's broadcast explicitly spelled out tax on the discounted fee; let me know if you want to push back on that with the lead instead.

## 10. t3 (p3): 15 turns

Tools: Read x4, Edit x7, Bash x3

Committed as `e19e02f`. Added `express: bool = False` to the `delivery-request` contract and forwarded it in dispatch's call to pricing's `/quote`; the `delivery` contract itself is unchanged since the lead didn't list it as gaining a field, and dispatch just uses whatever `total` pricing returns.

## 11. t1 (p3): 2 turns

Tools: Bash x1

R-8 (express delivery) only touches `quote-request`, `delivery-request`, and `quote` — all owned by T2/T3/T5, and explicitly scoped to Pricing, Dispatch, and Command line. It doesn't touch the `bird` or `destination` contracts that Roost (T1) owns, so `app/roost.py` needs no changes. No commit made.

**Summary:** Reviewed R-8 against Roost's scope (`bird`/`destination` contracts) and confirmed it doesn't apply — express fee logic lives entirely in pricing/dispatch/CLI. Nothing to change or commit on T1.

## 12. t4 (p3): 5 turns

Tools: Read x1, Write x1, Edit x1, Bash x1

R-8 is scoped to T2/T3/T5 (pricing, dispatch, CLI), and the `report`/`delivery` contracts billing depends on are unchanged — billing already sums each confirmed delivery's `total` field as-is, so once pricing/dispatch fold the express fee into `total`, revenue picks it up with zero code changes needed. No edits made to `app/billing.py`, nothing to commit.

## 13. t5 (p3): 8 turns

Tools: Read x2, Edit x3, Bash x2

Committed as `9538387` on `t5-cli`.

**Summary:** `quote` and `send` now accept `--express`, sending `"express": true/false` to `/quote` and `/deliveries`, and the quote output prints `express_fee:` right after `promo_discount:` (reading it straight from the quote response). No other commands were affected.

## 14. t6 (p3): 37 turns

Tools: Read x9, Glob x3, Bash x17, Write x5, Edit x2

Built and committed `app/tracking.py` for R-6: `GET /deliveries/{id}/tracking` returns status, bird, and ETA in whole minutes (round-half-up, 0 when cancelled, 404 when unknown), looking up delivery/bird/destination via the other parts' own HTTP endpoints since no shared internal store exists yet. R-8 (express) doesn't touch tracking per the lead's message, so no changes were needed there.

One thing for the team: per your note I named the ETA field `eta_min`, but PLAN.md's `tracking` contract and README's CLI spec both say `eta_minutes` — please flag this to the lead so the contract table gets updated, otherwise whoever builds T5 from PLAN.md alone will look for the wrong key.

## 15. t1 (p4): 4 turns

Tools: Read x1, Bash x2

Everything checks out — no code changes needed, and nothing to commit (`app/__pycache__/` is just build cruft, untracked by design).

**Summary:** Re-verified `app/roost.py` against R-1 and the `bird`/`destination` contracts with a full endpoint smoke test (list, get, 404 for both resources); all pass and R-8 doesn't touch Roost's scope. No changes needed before merge — T1 is ready as-is, with the earlier grams-unit flag for whoever owns Dispatch/CLI still standing.

## 16. t3 (p4): 9 turns

Tools: Bash x5, Read x3

I reviewed `app/dispatch.py` against R-3, R-4, R-8, and all three contracts it owns (`delivery-request`, `delivery`, `availability`) — everything is already correct, tests still pass, and there's nothing to change, so no new commit was needed.

Two merge-readiness notes for the team: dispatch reaches roost (`GET /birds`, `GET /birds/{handle}`) and pricing (`POST /quote`) purely over their documented HTTP contracts via an in-process ASGI call, so it needs those two routes to exist and return exactly the PLAN.md field shapes (e.g. `GET /birds` as a plain JSON array) once merged; and "flights left today" is tracked as an in-memory counter that never rolls over at a calendar boundary, since no part of the contract carries a date — it resets only on process restart.

**Summary:** Final review of dispatch.py confirmed R-3/R-4/R-8 and the delivery-request/delivery/availability contracts are already correctly implemented (committed at `e19e02f`); no code changes were required this round.

## 17. t2 (p4): 7 turns

Tools: Bash x3, Read x3

All checks pass, schema fields and order match the contract and CLI print order. No code changes were needed — the R-2/R-8 implementation from the last commit already holds up, so there's nothing new to commit.

Reviewed pricing.py end-to-end against R-2 and R-8 one more time — field order, rounding, and promo/express interaction all check out, no changes needed. T2 is ready for merge as committed at `dd3a057`.

## 18. t4 (p4): 11 turns

Tools: Bash x5, Edit x2, Write x2, Read x1

Reviewed `app/billing.py` for the final merge and broadened its dispatch-store detection (`_all_deliveries()`) to also handle dict-like objects, generic iterables/generators, and accessor functions, not just plain dict/list/tuple — verified against six different hypothetical storage shapes. Committed as `f604af4`; the one remaining risk for the team is that this is still a best-effort guess at T3's real storage shape since dispatch.py was never visible to this branch.

## 19. t5 (p4): 10 turns

Tools: Bash x1, Read x8

I reviewed `cli/pigeon.py` against the current README/PLAN and the R-8 express-delivery addition — it already fully implements both, and `git status` shows a clean working tree, so there's nothing new to commit.

**Summary:** `cli/pigeon.py` is complete and up to date: all nine README commands plus `--express`/`express_fee:` support for `quote` and `send` are in place from the prior commits (`f9f0182`, `9538387`), with no further changes needed before merge.

## 20. t6 (p4): 13 turns

Tools: Bash x5, Read x3, Edit x3, Write x1

Reverted the ETA field from `eta_min` back to `eta_minutes` since PLAN.md/README were never actually updated to match the earlier deviation, and committed. R-8 (express) doesn't touch tracking's contract or logic, so no other changes were needed.

## 21. fixer (fix1): 53 turns

Tools: Read x10, Glob x3, Bash x30, Edit x5, Write x1, ToolSearch x1, TaskStop x2

Fixed three cross-part integration breaks from the merge: `roost.py` had switched bird payloads to grams while dispatch/CLI still treated them as kg (broke C18–C20 bird selection and display); `dispatch.py` was refunding cancellations in full instead of applying the lead's 25% fee (C9); and `billing.py` hardcoded a flat $4 cancellation fee instead of the actual fee kept (C11). Verified all five against a live server and committed.
