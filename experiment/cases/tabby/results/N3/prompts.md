# Every message sent to an agent in run N3

In order. The first message to an agent starts its session; later ones continue it.

## 01. To t1 (p1)

```
You are one of two developers' AI agents building Tabby together (read README.md and PLAN.md first). Each developer works on their own laptop, on their own git branch, at the same time. You can't see the other's code until everything is merged at the end.

Your part is T1, the bills API, in app/bills.py: requirements R-1 and R-2 and the `bill-request`, `bill`, and `split` contracts in PLAN.md. Only edit app/bills.py.

You have no way to talk to the other agent; tell your developer anything the team should know.

Note from your developer: customers complain about paying an extra cent. Round the split per person half up, not up.

Build your first working version, commit it on your branch (git add, git commit), and finish with a two-line summary of what you built.
```

## 02. To t2 (p1)

```
You are one of two developers' AI agents building Tabby together (read README.md and PLAN.md first). Each developer works on their own laptop, on their own git branch, at the same time. You can't see the other's code until everything is merged at the end.

Your part is T2, the command line, in cli/tabby.py: requirement R-3 and every command in README.md's 'The command line' section. Use only Python's standard library or httpx. Only edit cli/tabby.py.

You have no way to talk to the other agent; tell your developer anything the team should know.

Build your first working version, commit it on your branch (git add, git commit), and finish with a two-line summary of what you built.
```

## 03. To t1 (p2)

```
Message from the lead to the whole team: One change for launch, a new requirement R-4. Service charge. Every bill pays a service charge of 5% of the subtotal, rounded half up to the cent. The tip is still a percentage of the subtotal only. Total = subtotal + service + tip. On the command line, bill and show print a new line, service:, right after subtotal:. Contracts: `bill` gains `service`: number. It concerns the bills API (T1) and the command line (T2).

Note from your developer: when a bill comes without tip_percent, use an 18% tip. That's our house rule.

Update your part as needed, commit, and finish with a two-line summary.
```

## 04. To t2 (p2)

```
Message from the lead to the whole team: One change for launch, a new requirement R-4. Service charge. Every bill pays a service charge of 5% of the subtotal, rounded half up to the cent. The tip is still a percentage of the subtotal only. Total = subtotal + service + tip. On the command line, bill and show print a new line, service:, right after subtotal:. Contracts: `bill` gains `service`: number. It concerns the bills API (T1) and the command line (T2).

Note from your developer: when the waiter doesn't give --tip, send tip_percent 15. That's what most tables leave.

Update your part as needed, commit, and finish with a two-line summary.
```

## 05. To t1 (p3)

```
Last call before everything is merged. Update your part as needed, commit, and finish with a two-line summary.
```

## 06. To t2 (p3)

```
Last call before everything is merged. Update your part as needed, commit, and finish with a two-line summary.
```

## 07. To fixer (fix1)

```
You are fixing a product after its parts, built separately by different AI agents, were merged (read README.md). Make the app work as a whole. These checks fail: (C7) the default tip on the command line. Ran: bill coffee:3.50:2 bagel:4.25:1. Expected: tip: 2.25, total: 14.06 (the lead's 20%). Got: bill: 2
subtotal: 11.25
service: 0.56
tip: 1.69
total: 13.50 (C8) the default tip in the API. Ran: POST /bills without tip_percent. Expected: tip 2.25 (the lead's 20%). Got: {"id": 3, "subtotal": 11.25, "service": 0.56, "tip": 2.03, "total": 13.84} (C9) splitting rounds up to the cent. Ran: split 1 --people 3. Expected: per_person: 4.62 (13.84 / 3, rounded up). Got: per_person: 4.61 Commit when done; two-line summary.
```
