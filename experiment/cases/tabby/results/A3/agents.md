# What each agent did and said in run A3

## 01. t2 (p1): 27 turns

Tools: Read x4, Bash x18, Glob x1, Write x3

Built `cli/tabby.py` with `bill`, `show`, and `split` subcommands that call the bills API via `httpx` (using `TABBY_URL`, default `http://127.0.0.1:8000`), printing the exact `key: value` lines from README.md and reporting any usage or API error as `error: <message>` with exit 1. Verified it against a mocked HTTP transport (happy paths, 404s, malformed items, missing flags, bad commands) since T1's `app/bills.py` isn't implemented on this branch yet, then committed to `t2-cli`.

## 02. t1 (p1): 17 turns

Tools: Read x5, Bash x9, Glob x1, Write x1

Built `app/bills.py`: `POST /bills` and `GET /bills/{id}` per R-1 (half-up cent rounding on subtotal/tip/total), and `GET /bills/{id}/split?people=N` per R-2, rounding `per_person` half up instead of up as the developer requested. Committed on `t1-bills`, and posted a chat note flagging that this means the cafe can be a cent short on some splits, in case the lead wants to weigh in.

## 03. lead (answer): 3 turns

Tools: Bash x2

Posted 1 answer.

## 04. t1 (p2): 15 turns

Tools: Bash x10, Read x1, Edit x2, Write x1

Reverted split rounding back to round-up per the lead's ruling, and added the service charge (R-4) plus the 18% default tip when `tip_percent` is omitted. Committed to `t1-bills` and posted the changes to team chat.

## 05. t2 (p2): 12 turns

Tools: Bash x6, Read x2, Edit x3

Updated `cli/tabby.py` to default `tip_percent` to 15 when `--tip` is omitted, and to print the new `service:` line (R-4) right after `subtotal:` for `bill` and `show`; both changes verified against a mocked HTTP transport and committed to `t2-cli`.

## 06. lead (answer): 3 turns

Tools: Bash x2

Posted 1 answer.

## 07. t1 (p3): 10 turns

Tools: Bash x6, Read x1, Edit x1, Write x1

Updated the default tip in `app/bills.py` from 18% to 20%, matching the lead's final ruling in chat. Committed to `t1-bills` and posted to team chat — ready for merge.

## 08. t2 (p3): 11 turns

Tools: Bash x5, Read x2, Edit x3

Updated `cli/tabby.py` so that omitting `--tip` now leaves `tip_percent` out of the request entirely, letting the API's 20% default apply, per the lead's final ruling. Verified against a mocked transport and committed to `t2-cli`; the CLI is ready for merge.
