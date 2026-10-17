# Every message sent to an agent in run B1

In order. The first message to an agent starts its session; later ones continue it.

## 01. To lead (plan)

```
You are the lead of Midflight project tabby-a101 (pass project_id tabby-a101 to every tool). Call project_status to find your own GitHub login: you are the lead. Then call propose_plan with exactly this plan, putting your login in place of OWNER in every task:

{
 "requirements": [
  {
   "id": "R-1",
   "description": "POST /bills creates a bill from its items (each a name, a price in dollars, and a quantity) and a tip_percent. Subtotal = sum of price x quantity. Tip = tip_percent % of the subtotal. Total = subtotal + tip. Money is in dollars with two decimals; round half up to the cent wherever a fraction of a cent appears. The reply is the bill with a new id. GET /bills/{id} returns a bill; an unknown id is a 404."
  },
  {
   "id": "R-2",
   "description": "GET /bills/{id}/split?people=N splits a bill between N people (N from 1): per_person = total / N, rounded up to the next cent so the cafe is never short. An unknown bill is a 404."
  },
  {
   "id": "R-3",
   "description": "The command line (cli/tabby.py) offers every command in README.md's 'The command line' section over HTTP and prints exactly the keys listed there."
  }
 ],
 "tasks": [
  {
   "id": "T1",
   "title": "Bills API (app/bills.py)",
   "owner": "OWNER",
   "branch": "t1-bills",
   "requirement_ids": [
    "R-1",
    "R-2"
   ],
   "provides": [
    "bill-request",
    "bill",
    "split"
   ],
   "consumes": []
  },
  {
   "id": "T2",
   "title": "Command line (cli/tabby.py)",
   "owner": "OWNER",
   "branch": "t2-cli",
   "requirement_ids": [
    "R-3"
   ],
   "provides": [],
   "consumes": [
    "bill-request",
    "bill",
    "split"
   ]
  }
 ],
 "contracts": [
  {
   "id": "bill-request",
   "provider_task": "T1",
   "consumer_tasks": [
    "T2"
   ],
   "fields": {
    "items": "array",
    "tip_percent": "number"
   }
  },
  {
   "id": "bill",
   "provider_task": "T1",
   "consumer_tasks": [
    "T2"
   ],
   "fields": {
    "id": "integer",
    "subtotal": "number",
    "tip": "number",
    "total": "number"
   }
  },
  {
   "id": "split",
   "provider_task": "T1",
   "consumer_tasks": [
    "T2"
   ],
   "fields": {
    "bill": "integer",
    "people": "integer",
    "per_person": "number"
   }
  }
 ]
}

Then call approve_plan with the version it returns and the reason "First plan". Finish with one line: the plan version you approved.
```

## 02. To t1 (p1)

```
You are one of two developers' AI agents building Tabby together (read README.md and PLAN.md first). Each developer works on their own laptop, on their own git branch, at the same time. You can't see the other's code until everything is merged at the end.

Your part is T1, the bills API, in app/bills.py: requirements R-1 and R-2 and the `bill-request`, `bill`, and `split` contracts in PLAN.md. Only edit app/bills.py.

Your team coordinates through Midflight: project tabby-a101, your task is T1. Your Midflight tools are connected; follow Midflight's instructions, and pass task_id T1 and project_id tabby-a101 to its tools.

Note from your developer: customers complain about paying an extra cent. Round the split per person half up, not up.

Build your first working version, commit it on your branch (git add, git commit), and finish with a two-line summary of what you built.
```

## 03. To t2 (p1)

```
You are one of two developers' AI agents building Tabby together (read README.md and PLAN.md first). Each developer works on their own laptop, on their own git branch, at the same time. You can't see the other's code until everything is merged at the end.

Your part is T2, the command line, in cli/tabby.py: requirement R-3 and every command in README.md's 'The command line' section. Use only Python's standard library or httpx. Only edit cli/tabby.py.

Your team coordinates through Midflight: project tabby-a101, your task is T2. Your Midflight tools are connected; follow Midflight's instructions, and pass task_id T2 and project_id tabby-a101 to its tools.

Build your first working version, commit it on your branch (git add, git commit), and finish with a two-line summary of what you built.
```

## 04. To lead (answer)

```
You are the lead of Midflight project tabby-a101 (pass project_id tabby-a101 to every tool). Call project_status. For each open escalation that is waiting for the lead, call resolve_escalation. If your decision sheet settles it, use resolution request_revision with the decision, word for word, as the reason. If nothing on the sheet settles it, use request_revision with the reason "Your call between the parts involved; keep to the plan." If it isn't a disagreement at all, dismiss it with a one-line reason. Don't change the plan, and don't act on anything that isn't an open escalation.

Your decision sheet, fixed before the project started:
1. Default tip: A bill without tip_percent gets a 20% tip. The command line sends no tip_percent when the waiter gives no --tip.
2. Splitting: The plan stands: the split per person is rounded up to the next cent, exactly as R-2 says.
3. Money and names: The plan stands: money in dollars with two decimals, and field names exactly as in the contracts.

Finish with one line: how many escalations you decided.
```

## 05. To lead (change)

```
You are the lead of Midflight project tabby-a101 (pass project_id tabby-a101 to every tool). Call project_status to find your own GitHub login: you are the lead. Then call propose_plan with exactly this plan, putting your login in place of OWNER in every task:

{
 "requirements": [
  {
   "id": "R-1",
   "description": "POST /bills creates a bill from its items (each a name, a price in dollars, and a quantity) and a tip_percent. Subtotal = sum of price x quantity. Tip = tip_percent % of the subtotal. Total = subtotal + tip. Money is in dollars with two decimals; round half up to the cent wherever a fraction of a cent appears. The reply is the bill with a new id. GET /bills/{id} returns a bill; an unknown id is a 404."
  },
  {
   "id": "R-2",
   "description": "GET /bills/{id}/split?people=N splits a bill between N people (N from 1): per_person = total / N, rounded up to the next cent so the cafe is never short. An unknown bill is a 404."
  },
  {
   "id": "R-3",
   "description": "The command line (cli/tabby.py) offers every command in README.md's 'The command line' section over HTTP and prints exactly the keys listed there."
  },
  {
   "id": "R-4",
   "description": "Service charge. Every bill pays a service charge of 5% of the subtotal, rounded half up to the cent. The tip is still a percentage of the subtotal only. Total = subtotal + service + tip. On the command line, bill and show print a new line, service:, right after subtotal:."
  }
 ],
 "tasks": [
  {
   "id": "T1",
   "title": "Bills API (app/bills.py)",
   "owner": "OWNER",
   "branch": "t1-bills",
   "requirement_ids": [
    "R-1",
    "R-2",
    "R-4"
   ],
   "provides": [
    "bill-request",
    "bill",
    "split"
   ],
   "consumes": []
  },
  {
   "id": "T2",
   "title": "Command line (cli/tabby.py)",
   "owner": "OWNER",
   "branch": "t2-cli",
   "requirement_ids": [
    "R-3",
    "R-4"
   ],
   "provides": [],
   "consumes": [
    "bill-request",
    "bill",
    "split"
   ]
  }
 ],
 "contracts": [
  {
   "id": "bill-request",
   "provider_task": "T1",
   "consumer_tasks": [
    "T2"
   ],
   "fields": {
    "items": "array",
    "tip_percent": "number"
   }
  },
  {
   "id": "bill",
   "provider_task": "T1",
   "consumer_tasks": [
    "T2"
   ],
   "fields": {
    "id": "integer",
    "subtotal": "number",
    "tip": "number",
    "total": "number",
    "service": "number"
   }
  },
  {
   "id": "split",
   "provider_task": "T1",
   "consumer_tasks": [
    "T2"
   ],
   "fields": {
    "bill": "integer",
    "people": "integer",
    "per_person": "number"
   }
  }
 ]
}

Then call approve_plan with the version it returns and the reason "Launch change: service charge". Finish with one line: the plan version you approved.
```

## 06. To t1 (p2)

```
Note from your developer: when a bill comes without tip_percent, use an 18% tip. That's our house rule.

Check in with Midflight first, then update your part as needed, commit, and finish with a two-line summary.
```

## 07. To t2 (p2)

```
Note from your developer: when the waiter doesn't give --tip, send tip_percent 15. That's what most tables leave.

Check in with Midflight first, then update your part as needed, commit, and finish with a two-line summary.
```

## 08. To lead (answer)

```
You are the lead of Midflight project tabby-a101 (pass project_id tabby-a101 to every tool). Call project_status. For each open escalation that is waiting for the lead, call resolve_escalation. If your decision sheet settles it, use resolution request_revision with the decision, word for word, as the reason. If nothing on the sheet settles it, use request_revision with the reason "Your call between the parts involved; keep to the plan." If it isn't a disagreement at all, dismiss it with a one-line reason. Don't change the plan, and don't act on anything that isn't an open escalation.

Your decision sheet, fixed before the project started:
1. Default tip: A bill without tip_percent gets a 20% tip. The command line sends no tip_percent when the waiter gives no --tip.
2. Splitting: The plan stands: the split per person is rounded up to the next cent, exactly as R-2 says.
3. Money and names: The plan stands: money in dollars with two decimals, and field names exactly as in the contracts.

Finish with one line: how many escalations you decided.
```

## 09. To t1 (p3)

```
Last call before everything is merged. Check in with Midflight first, then update your part as needed, commit, and finish with a two-line summary.
```

## 10. To t2 (p3)

```
Last call before everything is merged. Check in with Midflight first, then update your part as needed, commit, and finish with a two-line summary.
```

## 11. To fixer (fix1)

```
You are fixing a product after its parts, built separately by different AI agents, were merged (read README.md). Make the app work as a whole. These checks fail: (C7) the default tip on the command line. Ran: bill coffee:3.50:2 bagel:4.25:1. Expected: tip: 2.25, total: 14.06 (the lead's 20%). Got: bill: 2
subtotal: 11.25
service: 0.56
tip: 1.69
total: 13.50 (C8) the default tip in the API. Ran: POST /bills without tip_percent. Expected: tip 2.25 (the lead's 20%). Got: {"id": 3, "subtotal": 11.25, "tip": 2.03, "total": 13.84, "service": 0.56} (C9) splitting rounds up to the cent. Ran: split 1 --people 3. Expected: per_person: 4.62 (13.84 / 3, rounded up). Got: per_person: 4.61 Commit when done; two-line summary.
```
