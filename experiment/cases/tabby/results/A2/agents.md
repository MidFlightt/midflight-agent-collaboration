# What each agent did and said in run A2

## 01. t1 (p1): 22 turns

Tools: Read x5, Bash x13, Write x2, Edit x1

Committed as `038b211` on `t1-bills`.

Built `app/bills.py`: `POST /bills` (computes subtotal/tip/total with half-up cent rounding, assigns an id) and `GET /bills/{id}` / `GET /bills/{id}/split?people=N`, both 404 on unknown bills. Per your note, split's `per_person` rounds half up instead of always up — I flagged this deviation from PLAN.md's literal R-2 wording in the team chat so T2 and the lead are aware.

## 02. t2 (p1): 27 turns

Tools: Bash x22, Write x1, Read x2, Edit x1

Chat access needs your approval to run (`python3 tools/chat.py ...` keeps requiring approval I can't grant in this turn), so I committed without reading/posting to CHAT.md — let me know if you'd like me to retry once you approve it, or just run it yourself.

**Summary:** Built `cli/tabby.py` with `bill`, `show`, and `split` commands that call the Bills API via `httpx` and print the exact `key: value` lines from README.md, with `error: <message>` + exit 1 on any failure; committed on `t2-cli` as 7492ef5.

## 03. lead (answer): 3 turns

Tools: Bash x2

Posted 1 answer.

## 04. t1 (p2): 11 turns

Tools: Bash x4, Read x2, Edit x3, Write x1

Committed as `1970abd` on `t1-bills`.

Reverted split back to round-up per the lead's R-2 ruling, and added R-4's service charge (5% of subtotal, half up, included in total) plus a default 18% tip when `tip_percent` is omitted.

## 05. t2 (p2): 8 turns

Tools: Bash x5, Read x1, Edit x1

I couldn't read or post to the team chat — `tools/chat.py` keeps requiring approval I can't grant myself, so you may want to run it or approve it directly.

**Summary:** `cli/tabby.py`'s `bill` command now defaults `tip_percent` to 15 when `--tip` is omitted (was 0); committed as 97e5d25 on `t2-cli`, with chat read/post still blocked pending your approval.

## 06. lead (answer): 3 turns

Tools: Bash x2

Posted 1 answer.

## 07. t1 (p3): 8 turns

Tools: Bash x5, Read x1, Edit x1

Committed as `4d51bbe` on `t1-bills`.

Fixed the default tip to 20% (was mistakenly 18%) per the lead's correction; everything else — service charge, round-up split — was already in place from before, and the bills API is ready for merge.

## 08. t2 (p3): 16 turns

Tools: Bash x12, Read x1, Edit x2

I still can't reach the team chat this session (both read/fetch and post require approval I can't grant myself — the cached local ref for `origin/chat` only has the initial empty file, so I can't confirm I'm not missing something recent). You may want to run `python3 tools/chat.py read`/`post` yourself.

**Summary:** Applied the 15% default-tip change and added a catch-all in `main()` so any unexpected error (e.g. a malformed API response) prints a clean `error: <message>` line instead of a traceback, per README's contract; committed as 120d415 on `t2-cli`.

## 09. fixer (fix1): 37 turns

Tools: Bash x30, Read x2, Edit x3, Write x1

Committed as `9260f83`.

**Root cause:** the two parts were built independently and drifted — `app/bills.py` (T1) added a `service` field to the `bill` contract and a 20% default tip, but `cli/tabby.py` (T2) never learned about `service` and separately hard-coded its own 15% tip default, which it always sent to the API and so always overrode T1's default.

**Fix:** `cli/tabby.py` now prints `service:` right after `subtotal:`, and omits `tip_percent` (sends `None`) when `--tip` isn't given, letting the API's 20% default apply. Also updated README's example to match. Verified both C5 and C7 against a live server with the exact expected output.
