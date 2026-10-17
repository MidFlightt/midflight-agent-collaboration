# What each agent did and said in run N2

## 01. t1 (p1): 18 turns

Tools: Read x5, Bash x10, Write x2

Committed on `t1-bills`. Built the `app/bills.py` FastAPI router: `POST /bills` creates a bill (subtotal/tip/total rounded half-up to the cent, in-memory ids starting at 1), `GET /bills/{id}` fetches it or 404s, `GET /bills/{id}/split?people=N` returns `per_person` (404 for unknown bill, 422 for `people<1`).

One thing worth telling your teammate: PLAN.md's R-2 says per-person should round **up** ("so the cafe is never short"), but you asked for half-up rounding to kill the extra-cent complaints — I implemented half-up as requested. That means on some splits the sum of `per_person × people` will land a cent under the bill total (e.g. a $10.00 bill split 3 ways is `3.33` each, totaling $9.99). Since the `split` contract only fixes field names/types, not rounding direction, this won't break T2's integration, but it's a real behavior difference from the written spec that the other developer should know about.

## 02. t2 (p1): 26 turns

Tools: Read x7, Bash x14, Glob x1, Write x1, Edit x2

Committed. Here's what the team should know:

**Built:** `cli/tabby.py` now implements `bill`, `show`, and `split` per README, talking to the API via `httpx` using the `bill-request`/`bill`/`split` contracts from PLAN.md (`POST /bills`, `GET /bills/{id}`, `GET /bills/{id}/split?people=N`). Any failure — bad args, connection error, 404, other server error — prints a single `error: <message>` line and exits 1, per R-3.

**Heads up for the other dev (T1):**
- `app/bills.py` is still just a stub (no routes), as expected since that's your side — I built against the contract in PLAN.md, not against running code.
- I couldn't actually run the CLI end-to-end: this sandbox blocks all Python/`uv` execution pending an approval that never resolved, even for `python3 -m py_compile`. I traced the logic by hand but **please smoke-test `python -m cli.tabby bill coffee:3.50:2 --tip 18` etc. once your API is up**, per the README's `uv run uvicorn...` instructions.
- Assumption to confirm: on 404 for `show`/`split` I print `error: bill not found`; for other non-2xx responses I look for a string `detail` field in the JSON body and otherwise fall back to `error: server returned <status>`. If your error bodies look different, that fallback text is what waiters will see.
- `--tip` is optional and defaults to `tip_percent: 0` if omitted (README doesn't specify a default).

## 03. t1 (p2): 11 turns

Tools: Read x2, Edit x4, Bash x4

Committed on `t1-bills`. Added a 5%-of-subtotal service charge (half-up to the cent, folded into `total`) and made `tip_percent` optional, defaulting to 18% per the house rule when omitted while still honoring an explicit `0`.

The `bill` contract now has fields in order `id, subtotal, service, tip, total` — T2 needs to add the `service:` line right after `subtotal:` in `bill`/`show` output to match.

## 04. t2 (p2): 4 turns

Tools: Edit x1, Read x1, Bash x1

Updated `cli/tabby.py` for R-4: `bill`/`show` now print `service:` after `subtotal:`, and `bill` sends `tip_percent: 15` by default when `--tip` is omitted. Commit `b9d32dc` is in; `split` needed no changes since its output is unaffected.

## 05. t1 (p3): 8 turns

Tools: Bash x4, Read x3

I re-verified `app/bills.py` against R-1, R-2, and R-4 with a full test pass (normal bill, default-18%-tip, zero-tip, empty items, 404s, split rounding, invalid `people`) — everything already checked in from the last commit holds up, so there's nothing to change or commit this round.

No new commit needed: T1's bills API (create/get/split, service charge, 18% default tip) is complete and verified as-is, ready to merge on `t1-bills`.

## 06. t2 (p3): 6 turns

Tools: Bash x2, Read x3

I reviewed `cli/tabby.py` against all requirements communicated so far — R-3, R-4 (service charge line), and the 15% default tip — and traced each command by hand again. The file already covers everything correctly from the last commit (`b9d32dc`); no further changes were needed, so the working tree is clean with nothing new to commit.

**Summary:** `cli/tabby.py` is complete and unchanged this round — `bill`/`show` print `bill:`, `subtotal:`, `service:`, `tip:`, `total:` and default to `tip_percent: 15` when `--tip` is omitted, `split` is untouched. Ready for merge on my end; the only open item is that I couldn't execute Python in this sandbox to run a live smoke test, so a quick manual run against the merged API is worth doing.

## 07. fixer (fix1): 38 turns

Tools: Read x3, Bash x28, Edit x3, Write x1, ToolSearch x1, TaskStop x1

Fixed and committed (`aaf25d9`): the API and CLI each had their own default tip (18% and 15%, with the CLI's always winning since it never sent `null`), so I unified both on 20% and had the CLI defer to the API's default instead of hardcoding one. Split rounding used round-half-up instead of always-round-up, so I switched it to `ROUND_CEILING`. Verified C7/C8/C9 all produce the expected values via direct API calls (CLI's HTTP behavior is identical, confirmed by code review since local sandbox network-approval blocked running the CLI binary directly).
