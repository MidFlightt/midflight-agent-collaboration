# What each agent did and said in run N2

## 01. t1 (p1): 22 turns

Tools: Read x6, Bash x12, Write x1, ToolSearch x1, TaskStop x1

Committed on `t1-catalog`. Tested live: list, skill filter, get-by-handle, and 404-for-unknown all work correctly via HTTP.

**Summary:** Built `app/catalog.py` with the 6 agents from README (handle, name, skills, rate, capacity), exposing both HTTP routes (`GET /agents`, `GET /agents?skill=X`, `GET /agents/{handle}`) and plain Python functions (`list_agents`, `get_agent`) for in-process use by other parts.

**Notes for the team:** Pricing and Bookings run in the same FastAPI process, so they should `import app.catalog` and call `get_agent(handle)`/`list_agents(skill)` directly rather than making HTTP calls to themselves. `get_agent` returns `None` on an unknown handle (not an exception) so each part can format its own `error: <message>` to match the CLI spec. `Agent.capacity` is the static weekly capacity from the README — tracking "hours left" per week is Bookings' own job (rules 7/8), not catalog's.

## 02. t2 (p1): 23 turns

Tools: Bash x12, Read x6, Write x4

Committed on `t2-pricing`.

**Built:** `app/pricing.py` implements rules 1–6 via `price_order(lines, promo=None)` (reusable in-process, e.g. for `bookings.py`) plus a `POST /quote` HTTP endpoint, rounding half-up to whole credits at each line item.

**For the team:** since `app/catalog.py` is still an empty stub on my branch, I hardcoded the agent/rate table from the README inside `pricing.py` rather than importing it — worth switching to a shared source at merge time so rates can't drift between the two files. I also didn't cap the promo/volume discounts at the subtotal, so a cheap order + `BEEPBOOP` can go negative before tax; the README doesn't say to clamp it, but flag if that's unwanted.

## 03. t3 (p1): 22 turns

Tools: Bash x11, Read x7, Write x2, Edit x1

Committed on `t3-bookings`.

**For the team:** `app/bookings.py` currently embeds its own copy of the agent catalog (rates/capacities) and the pricing calculation (rules 1–6), since `catalog.py`/`pricing.py` were empty stubs when I built this — at merge time, swap those local copies for imports from the real `catalog.py`/`pricing.py` so pricing logic lives in one place. HTTP endpoints I picked (may need aligning with the CLI branch): `POST /bookings`, `GET /bookings/{id}`, `POST /bookings/{id}/cancel`, `GET /agents/{handle}/availability`. For the reports branch: `from app.bookings import list_bookings` gives direct Python access to all bookings (status, lines, total) — no HTTP call needed.

**Summary:** Built `app/bookings.py` with booking creation (atomic capacity check + reservation), lookup, cancellation (hours returned), and per-agent weekly availability, all tested end-to-end via FastAPI's TestClient. Next step is reconciling the duplicated catalog/pricing data with the other branches once everything merges.

## 04. t4 (p1): 22 turns

Tools: Bash x11, Read x8, Write x2

Committed on `t4-reports`. One thing the team needs to know, flagging for the developer:

**Interface assumption:** `app/reports.py`'s `GET /report` reads directly from `app.bookings.bookings` (not yet built), expecting it to be a dict of `booking_id -> {"status": "confirmed"|"cancelled", "total": <int credits>, "lines": {agent_handle: hours}}`. I used `getattr(..., {})` so the app doesn't crash while bookings.py is still a stub, but whoever builds bookings.py needs to actually name their store `bookings` with that shape (or reports.py needs a follow-up edit at merge time to match whatever shape they picked). I also assumed "revenue" = sum of `total` for confirmed bookings only (cancelled bookings earn nothing).

**Summary:** Added `GET /report` in `app/reports.py`, returning `revenue`, `confirmed`, `cancelled`, and per-agent `hours` (confirmed bookings only), computed live from `app.bookings`'s in-memory store. Verified with a mock booking dataset via FastAPI's TestClient; next step is reconciling the assumed `bookings` data shape with whatever bookings.py actually implements.

## 05. t5 (p1): 63 turns

Tools: Read x11, Bash x46, Write x3, ToolSearch x1, TaskStop x1

Clean commit on `t5-cli`, only `cli/hirebot.py` changed.

**Summary:** Built `cli/hirebot.py`, implementing all seven README commands (`agents`, `quote`, `book`, `show`, `cancel`, `availability`, `report`) against an assumed REST/JSON contract (documented in the file's docstring), validated end-to-end with a throwaway mock FastAPI server. Since `app/*.py` are still empty stubs from the other agents, there's no real API yet to confirm against — the team should check my assumed endpoint paths and JSON field names (e.g. `/quote`, `/bookings/<id>/cancel`, `/agents/<handle>/availability`, field names like `handle`/`capacity`/`booking`/`hours`) against whatever `catalog.py`/`pricing.py`/`bookings.py`/`reports.py` end up exposing, and adjust either side during integration.

## 06. t1 (p2): 2 turns

Tools: Bash x1

Checked both changes against catalog's scope — neither requires edits to `app/catalog.py`.

- **Half-hour bookings**: the catalog only holds each agent's static weekly capacity and hourly rate (whole numbers from the README, e.g. `meeting-ghost` capacity=30, rate=150). Order hours, fractional "hours left" tracking, and rounding live entirely in `pricing.py`/`bookings.py` — catalog never sees an order's hours, so nothing here changes.
- **Rush orders**: the rush fee is computed purely from an order's subtotal/discounts, which is `pricing.py`'s domain. Catalog has no concept of orders or fees.

I verified there's nothing to commit (`git status` clean aside from an untracked `__pycache__`), so I made no commit — an empty one would be noise.

**Summary:** Reviewed both launch changes against `app/catalog.py`'s responsibility (agent listing/filter/lookup) and found no changes needed — both land entirely in pricing/bookings. Flag for the team: if bookings tracks "hours left" per agent, it should keep that as its own float state rather than assuming catalog's `capacity` field changes type.

## 07. t2 (p2): 9 turns

Tools: Read x1, Edit x3, Write x1, Bash x3

Committed on `t2-pricing`.

**Built:** `price_order` now accepts half-hour increments (rejecting anything not a positive multiple of 0.5) and a `rush` flag that adds a 25% rush fee folded into the tax base and total; `/quote` gained a `rush` request field and `rush_fee` response field (0 when not rushed, ordered right after `promo_discount`).

## 08. t3 (p2): 11 turns

Tools: Read x1, Write x2, Bash x7

Committed on `t3-bookings`. Note for the team: `app/pricing.py`'s `--rush` on `quote` needs to match my formula exactly — rush_fee = 25% of (subtotal − volume_discount − promo_discount), tax = 8% of (that + rush_fee), total includes rush_fee — and reports.py's revenue must sum confirmed bookings only, since cancellations are now full refunds.

**Summary:** Added half-hour booking support (hours as any multiple of 0.5, tracked exactly via Decimal through capacity/availability) and rush-fee pricing (25% surcharge that flows into tax and total, 0 when not rushed) to `app/bookings.py`, verified against hand-calculated cases including rounding edge cases and cancellation refunds.

## 09. t4 (p2): 7 turns

Tools: Read x1, Edit x1, Write x1, Bash x3

Updated `/report` to add a 20% cancellation fee (rounded half up) onto revenue for cancelled bookings, and switched hours-per-agent to float so half-hour increments pass through correctly; the rush fee needed no change since it's already baked into each booking's stored total.

One flag for the team: my cancellation-fee math assumes bookings.py leaves a cancelled booking's `total` as the **original** order price rather than overwriting it with just the fee amount — worth confirming with whoever's building `bookings.py` at merge time.

## 10. t5 (p2): 18 turns

Tools: Read x3, Edit x4, Bash x9, TaskStop x1

**Summary:** Updated `cli/hirebot.py` to accept half-hour line items (`agent=2.5`, validated as positive multiples of 0.5 via `Decimal`) and to add a `--rush` flag on `quote`/`book` that's sent as `rush` in the request body and prints a new `rush_fee:` line right after `promo_discount:`. Committed as `8924536` on `t5-cli`; the assumed JSON contract for `rush`/`rush_fee`/fractional `hours` is documented in the file's docstring for the other agents to reconcile against.

## 11. fixer (fix1): 51 turns

Tools: Read x13, Edit x9, Bash x27, Write x5, Grep x1


