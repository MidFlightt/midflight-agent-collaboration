# What each agent did and said in run N3

## 01. t1 (p1): 21 turns

Tools: Read x5, Bash x12, Write x3

**Summary:** Built `POST /bills`, `GET /bills/{id}`, and `GET /bills/{id}/split` in `app/bills.py`, using `Decimal` for exact half-up rounding to the cent and matching the `bill-request`/`bill`/`split` contracts; all manual tests pass and the change is committed on `t1-bills`.

**Heads up for the team:** PLAN.md's R-2 says split should round *up* to the next cent ("so the cafe is never short"), but per your note I implemented round-half-up instead to stop overcharging customers. This means T2 (and anyone testing against the written spec) will see per-person amounts that are sometimes a cent *lower* than R-2 describes — worth confirming T2 doesn't assume ceiling rounding, since the contract table doesn't capture this deviation.

## 02. t2 (p1): 27 turns

Tools: Read x7, Glob x2, Write x1, Bash x15, Edit x1

Built `cli/tabby.py` with `bill`, `show`, and `split` commands that call the Bills API via httpx, parsing items/flags per README, printing the exact `key: value` lines, and reporting failures as `error: <message>` with exit code 1 (including unreachable server, 404s via the `detail` field, and bad input). Committed as `cf98e57` on `t2-cli`.

One note for the team: I couldn't do a live end-to-end test — `app/bills.py` (T1) is still just an empty router stub, and this sandbox blocks any `python3 -m`/`-c` execution (only `--version` is permitted), so I verified the CLI by careful manual trace instead of running it. Once T1's endpoints land, it'd be worth a quick smoke test of all three commands against a running server.

## 03. t1 (p2): 10 turns

Tools: Read x2, Edit x3, Write x1, Bash x3

**Summary:** Added the 5% service charge (half-up rounded, folded into `total`) and made `tip_percent` default to 18 when omitted, matching R-4 and the house rule; committed on `t1-bills`.

Note for T2: the `bill` JSON now has `service` between `subtotal` and `tip` so the CLI can print `service:` right after `subtotal:` in that order.

## 04. t2 (p2): 6 turns

Tools: Edit x1, Read x3, Bash x1

Updated `print_bill` to show `service:` between `subtotal:` and `tip:`, and changed `cmd_bill`'s default `tip_percent` from 0 to 15 when `--tip` is omitted. Committed as `f664890` on `t2-cli`.

## 05. t1 (p3): 8 turns

Tools: Bash x3, Read x3, Write x1

I reviewed `app/bills.py` against R-1, R-2, and R-4 plus the house rules (default 18% tip, half-up split) and re-verified with tests — everything already matches, including edge cases like explicit `tip_percent: 0` not triggering the default. No code changes were needed, so there's nothing new to commit; the branch is already at `b296672` with the complete bills API ready for merge.

## 06. t2 (p3): 7 turns

Tools: Read x4, Bash x2

I reviewed `cli/tabby.py` against R-3, R-4, and the 15% default-tip note — it already prints `service:` right after `subtotal:`, defaults `tip_percent` to 15 when `--tip` is omitted, and nothing else in this final call requires changes, so no new commit was needed.

Final state is commit `f664890` on `t2-cli`: the CLI implements `bill`/`show`/`split` over HTTP with the exact key order from README (including `service:`), defaults to a 15% tip, and reports failures as `error: <message>` with exit 1 — ready to merge.

## 07. fixer (fix1): 46 turns

Tools: Read x5, Bash x33, Edit x4, Write x1, ToolSearch x1, TaskStop x1

Fixed and verified against a live server: the API's default tip was 18% and the CLI separately hardcoded 15% (always overriding the API), so I unified both on the lead's 20% default and made the CLI omit `tip_percent` when `--tip` is absent, letting the API own that rule. Split was also rounding to nearest cent instead of up, so I switched it to `ROUND_UP`. All three checks (C7, C8, C9) now pass and the fix is committed as `4a09a23`.
