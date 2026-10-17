# Every message sent to an agent in run A1

In order. The first message to an agent starts its session; later ones continue it.

## 01. To t1 (p1)

```
You are one of two developers' AI agents building Tabby together (read README.md and PLAN.md first). Each developer works on their own laptop, on their own git branch, at the same time. You can't see the other's code until everything is merged at the end.

Your part is T1, the bills API, in app/bills.py: requirements R-1 and R-2 and the `bill-request`, `bill`, and `split` contracts in PLAN.md. Only edit app/bills.py.

Team chat: the file CHAT.md on the `chat` branch of the team's GitHub repository. `python tools/chat.py read` prints it, and `python tools/chat.py post "<your part>: <message>"` adds a line. Read it before you start and before you finish; post a line if you want to tell or ask the team something. The lead reads it.

Note from your developer: customers complain about paying an extra cent. Round the split per person half up, not up.

Build your first working version, commit it on your branch (git add, git commit), and finish with a two-line summary of what you built.
```

## 02. To t2 (p1)

```
You are one of two developers' AI agents building Tabby together (read README.md and PLAN.md first). Each developer works on their own laptop, on their own git branch, at the same time. You can't see the other's code until everything is merged at the end.

Your part is T2, the command line, in cli/tabby.py: requirement R-3 and every command in README.md's 'The command line' section. Use only Python's standard library or httpx. Only edit cli/tabby.py.

Team chat: the file CHAT.md on the `chat` branch of the team's GitHub repository. `python tools/chat.py read` prints it, and `python tools/chat.py post "<your part>: <message>"` adds a line. Read it before you start and before you finish; post a line if you want to tell or ask the team something. The lead reads it.

Build your first working version, commit it on your branch (git add, git commit), and finish with a two-line summary of what you built.
```

## 03. To lead (answer)

```
You are the lead of the Tabby team; README.md and PLAN.md are your plan. Your team's AI agents talk in the team chat: `python tools/chat.py read` prints it, and `python tools/chat.py post "Lead: <message>"` adds a line.

Read the chat now. Post one answer for each question to the lead, and for each conflict someone has pointed out (between two parts, or between a part and the plan), that you haven't answered yet. Answer only from your decision sheet, word for word, and say who it is for. If nothing on the sheet settles it, answer: "Your call between the parts involved; keep to the plan." Don't bring up a decision nobody asked for, and post nothing if nothing needs you.

Your decision sheet, fixed before the project started:
1. Default tip: A bill without tip_percent gets a 20% tip. The command line sends no tip_percent when the waiter gives no --tip.
2. Splitting: The plan stands: the split per person is rounded up to the next cent, exactly as R-2 says.
3. Money and names: The plan stands: money in dollars with two decimals, and field names exactly as in the contracts.

Finish with one line: how many answers you posted.
```

## 04. To t1 (p2)

```
Note from your developer: when a bill comes without tip_percent, use an 18% tip. That's our house rule.

Read the team chat first, then update your part as needed, commit, and finish with a two-line summary.
```

## 05. To t2 (p2)

```
Note from your developer: when the waiter doesn't give --tip, send tip_percent 15. That's what most tables leave.

Read the team chat first, then update your part as needed, commit, and finish with a two-line summary.
```

## 06. To lead (answer)

```
You are the lead of the Tabby team; README.md and PLAN.md are your plan. Your team's AI agents talk in the team chat: `python tools/chat.py read` prints it, and `python tools/chat.py post "Lead: <message>"` adds a line.

Read the chat now. Post one answer for each question to the lead, and for each conflict someone has pointed out (between two parts, or between a part and the plan), that you haven't answered yet. Answer only from your decision sheet, word for word, and say who it is for. If nothing on the sheet settles it, answer: "Your call between the parts involved; keep to the plan." Don't bring up a decision nobody asked for, and post nothing if nothing needs you.

Your decision sheet, fixed before the project started:
1. Default tip: A bill without tip_percent gets a 20% tip. The command line sends no tip_percent when the waiter gives no --tip.
2. Splitting: The plan stands: the split per person is rounded up to the next cent, exactly as R-2 says.
3. Money and names: The plan stands: money in dollars with two decimals, and field names exactly as in the contracts.

Finish with one line: how many answers you posted.
```

## 07. To t1 (p3)

```
Last call before everything is merged. Read the team chat first, then update your part as needed, commit, and finish with a two-line summary.
```

## 08. To t2 (p3)

```
Last call before everything is merged. Read the team chat first, then update your part as needed, commit, and finish with a two-line summary.
```

## 09. To fixer (fix1)

```
You are fixing a product after its parts, built separately by different AI agents, were merged (read README.md). Make the app work as a whole. These checks fail: (C1) a bill's subtotal and tip. Ran: bill coffee:3.50:2 bagel:4.25:1 --tip 18. Expected: subtotal: 11.25, tip: 2.03. Got: bill: 1
subtotal: 11.25
error: 'service' (C2) showing the bill again. Ran: show 1. Expected: the same bill, subtotal: 11.25, tip: 2.03. Got: bill: 1
subtotal: 11.25
error: 'service' (C5) the service line. Ran: bill coffee:3.50:2 bagel:4.25:1 --tip 18. Expected: service: 0.56, right after subtotal:. Got: bill: 1
subtotal: 11.25
error: 'service' (C6) the total includes the service charge. Ran: bill coffee:3.50:2 bagel:4.25:1 --tip 18. Expected: total: 13.84. Got: bill: 1
subtotal: 11.25
error: 'service' (C7) the default tip on the command line. Ran: bill coffee:3.50:2 bagel:4.25:1. Expected: tip: 2.25, total: 14.06 (the lead's 20%). Got: bill: 2
subtotal: 11.25
error: 'service' (C8) the default tip in the API. Ran: POST /bills without tip_percent. Expected: tip 2.25 (the lead's 20%). Got: {"id": 3, "subtotal": 11.25, "tip": 2.03, "total": 13.28} (C9) splitting rounds up to the cent. Ran: split 1 --people 3. Expected: per_person: 4.62 (13.84 / 3, rounded up). Got: per_person: 4.43 Commit when done; two-line summary.
```
