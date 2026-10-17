# What each agent did and said in run A1

## 01. t1 (p1): 28 turns

Tools: Read x6, Bash x18, Write x3

I couldn't reach the chat branch in this session — network git commands (and script execution in general) are being blocked by the sandbox here, while local git works fine. You'll need to run this yourself (or re-run with those permissions enabled):

```
python tools/chat.py post "T1: split now rounds per-person half up, not up to the next cent (per dev request, to stop overcharging by a cent) — heads up this differs from R-2's literal wording, flagging for the lead"
```

Summary: Implemented `app/bills.py` — `POST /bills`, `GET /bills/{id}`, and `GET /bills/{id}/split` with decimal-based half-up rounding throughout (subtotal, tip, total, and per-person split), matching the `bill-request`/`bill`/`split` contracts and returning 404 for unknown bills. Per your note, the split rounds half up instead of always up, so the cafe can occasionally be short a cent on an unevenly-divided split — committed on `t1-bills` as 821afdf.

## 02. t2 (p1): 48 turns

Tools: Read x5, Bash x37, Write x2, Edit x1, ToolSearch x1, TaskStop x1

Built `cli/tabby.py` implementing R-3: the `bill`, `show`, and `split` commands parse README's exact syntax, call the bills API over HTTP via `httpx`/`TABBY_URL`, and print exactly the required `key: value` lines or a single `error:` line with exit 1 on any failure.

Verified against a mock server matching the T1 contract (app/bills.py isn't implemented yet) — create/show/split all format correctly, and bad input, 404s, and connection failures all produce the correct error format. Committed on `t2-cli` as c81c9ce, and posted a note to team chat about the error-detail assumption for T1 to confirm.

## 03. lead (answer): 4 turns

Tools: Bash x1, Read x2

I read the team chat. T2 posted one message — a note about CLI error-handling built against a mock (since `app/bills.py` is still a stub), ending with "let me know if your error responses use a different shape." That's addressed to T1 (the Bills API owner) about an implementation detail not covered in the contracts or my decision sheet — it's not a question to me, and no conflict between parts or between a part and the plan has been raised.

Nothing needs me right now, so I'm not posting anything.

0 answers posted.

## 04. t1 (p2): 8 turns

Tools: Bash x5, Read x1, Edit x1

Still blocked — I was unable to read or post to team chat this session (local git works, but network git operations aren't being approved). You may want to check CHAT.md yourself, and post if you want the team to know about this change.

Summary: `BillRequest.tip_percent` now defaults to 18 when omitted from the JSON body, so a bill posted without that field gets an 18% tip instead of being rejected. Committed on `t1-bills` as 851ef5f.

## 05. t2 (p2): 13 turns

Tools: Bash x7, Read x2, Edit x2, TaskStop x1

Updated `cli/tabby.py`: `bill`/`show` now print `service:` right after `subtotal:`, and `bill` defaults to a 15% tip when `--tip` is omitted. Verified against an updated mock server and committed as be175d3 on `t2-cli`.

## 06. lead (answer): 3 turns

Tools: Bash x2

T2's latest update has the CLI defaulting `tip_percent` to 15 when `--tip` is omitted — that conflicts with the plan, so I posted the decision-sheet answer for T2: the CLI should send no `tip_percent` at all, and the API applies the 20% default.

1 answer posted.

## 07. t1 (p3): 10 turns

Tools: Bash x7, Read x1, Edit x1

I still can't reach the chat branch this session (git fetch/push, even to the local bare repo path, keeps getting blocked as outside-directory access) — I wasn't able to confirm what T2 or the lead have said, including about the rounding deviation I never actually got to post. Since you said this is the last call before merge, flag two things to the lead yourself if you get a chance: (1) the split endpoint rounds half-up instead of R-2's literal "round up," per your request, so the cafe can occasionally be short a cent; (2) bills posted without `tip_percent` now default to 18%.

Summary: Re-reviewed `app/bills.py` against the R-1/R-2 requirements and all three contracts — logic holds, so I only corrected a stale comment that wrongly claimed the rounding deviation had been posted to chat. Committed on `t1-bills` as bdd5228.

## 08. t2 (p3): 15 turns

Tools: Bash x7, Read x3, Edit x3, TaskStop x1

Fixed `cli/tabby.py` so `bill` omits `tip_percent` entirely from the request when `--tip` isn't given (letting the API's 20% default apply), instead of hardcoding a CLI-side default. Verified the request body against a mock server and committed as 0e4a9eb on `t2-cli`.

## 09. fixer (fix1): 48 turns

Tools: Read x9, Bash x28, Edit x7, Write x1, ToolSearch x1, TaskStop x1

Committed. Summary: `app/bills.py` was missing R-4's `service` field entirely (causing the CLI's `error: 'service'`), defaulted `tip_percent` to 18% instead of the lead's final 20%, and rounded splits half-up instead of up as R-2 requires — all three are now fixed and verified against a live test server, and README/PLAN are updated to match.
