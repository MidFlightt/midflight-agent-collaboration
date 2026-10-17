# What each agent did and said in run B3

## 01. lead (plan): 5 turns

Tools: ToolSearch x1, project_status x1, propose_plan x1, approve_plan x1

Approved plan version: **1**

## 02. t1 (p1): 24 turns

Tools: Read x5, ToolSearch x1, check_in x2, Bash x10, submit_claim x1, Glob x1, Write x2, Edit x1

Built `app/bills.py`: POST/GET `/bills` and `/bills/{id}/split`, with half-up cent rounding throughout (matching the README's own worked example) and 404s for unknown ids. Note: I used half-up rounding for `per_person` per your instruction, but this contradicts R-2's written text ("rounded up... so the cafe is never short") — Midflight flagged this conflict as an open question for the team lead to resolve, since it affects what T2 (the CLI) will receive.

## 03. t2 (p1): 17 turns

Tools: Read x5, Bash x6, ToolSearch x1, my_projects x1, check_in x1, submit_claim x1, Write x1

This needs your approval to run — could you approve the Bash tool call so I can test `python3 -m cli.tabby bogus`, or let me know if you'd rather I skip live execution and rely on code review alone?

## 04. lead (answer): 2 turns

Tools: project_status x1

Checked project status: **0 open escalations**. There's a "decision in force" (E-1, about split rounding) already agreed between T1 and T2, but it's not an open escalation waiting for the lead, so per instructions I'm not acting on it.

Decided 0 escalations.

## 05. lead (change): 4 turns

Tools: project_status x1, propose_plan x1, approve_plan x1

Approved plan version: **2**

## 06. t1 (p2): 24 turns

Tools: check_in x2, ToolSearch x2, acknowledge_directive x1, submit_claim x4, Bash x6, Read x2, Edit x5, Write x1

Added R-4's 5% service charge and made `tip_percent` default to 18% when omitted, per your house rule. One thing needs your attention: this 18% API-side default conflicts with a cross-team decision (E-3) that has the CLI always send `tip_percent` explicitly, defaulting to 15% client-side instead — Midflight flagged it, I implemented your instruction anyway and logged the conflict on claim C-1 for the lead to reconcile.

## 07. t2 (p2): 14 turns

Tools: check_in x2, ToolSearch x1, acknowledge_directive x3, submit_claim x2, Edit x3, Read x1, Bash x1

Running Python requires your approval in this sandbox — could you approve it, or should I skip execution and rely on a careful code read instead?

## 08. lead (answer): 2 turns

Tools: project_status x1

Checked project status: **0 open escalations**. There's a decision in force (E-3, about CLI tip default) already settled by Midflight, but it's not an open escalation awaiting the lead, so per instructions I'm not acting on it.

Decided 0 escalations.

## 09. t1 (p3): 4 turns

Tools: check_in x1, Bash x2

Everything still checks out — no code changes were needed since the last commit, and the working tree is clean, so nothing new to commit. Current HEAD (`2a21e18`) is the final state going into merge: R-1 (create/get bills), R-2 (split), and R-4 (service charge) all implemented and tested, with `tip_percent` defaulting to 18% when omitted.

Two conflicts remain unresolved on Midflight claim C-1 for the lead to settle at merge time: per-person split rounding (half-up, per your instruction, vs. R-2's literal "always round up"), and the tip_percent default value/location (18% API-side, per your instruction, vs. the CLI's 15% client-side default settled under E-3).

## 10. t2 (p3): 4 turns

Tools: check_in x1, Bash x2

Committed as `77b8616` on `t2-cli`. Built `cli/tabby.py`'s `bill`/`show`/`split` commands against the T1 contracts (R-3), printing `bill:`/`subtotal:`/`service:`/`tip:`/`total:` or `per_person:` and a single `error:` line with exit 1 on any failure; `bill` defaults `tip_percent` to 15 and always sends it explicitly, matching R-4 and Midflight's E-3 ruling.

## 11. fixer (fix1): 34 turns

Tools: Read x5, Glob x1, Grep x2, Bash x18, Edit x3, ToolSearch x2, Monitor x1, TaskStop x1

Committed as `bc6c443`.

**Summary:** The API and CLI had each guessed their own default tip (18% and 15%) instead of the lead's 20%, and the split endpoint rounded half-up instead of up-to-the-cent as the plan specified — fixed both in `app/bills.py` and `cli/tabby.py`, verified against all three failing cases (C7/C8/C9), and committed.
