# Every message sent to an agent in run B7

In order. The first message to an agent starts its session; later ones continue it.

## 01. To t1 (p1)

```
You are one of five developers' AI agents building HireBot together (read README.md first). Each agent builds one part on its own git branch, in its own folder, at the same time; you can't see the others' work until everything is merged at the end.

Your part: the catalog, in app/catalog.py. Build the API that lists the agents from README.md (handle, name, skills, hourly rate, weekly capacity), can filter them by skill, and returns one agent by its handle. Only edit app/catalog.py.

Your team coordinates through Midflight: project hirebot-7bf3, your task is T1. Your Midflight tools are connected; follow Midflight's instructions, and pass task_id T1 and project_id hirebot-7bf3 to its tools.

Build your first working version, commit it on your branch (git add, git commit), and finish with a two-line summary of what you built.
```

## 02. To t2 (p1)

```
You are one of five developers' AI agents building HireBot together (read README.md first). Each agent builds one part on its own git branch, in its own folder, at the same time; you can't see the others' work until everything is merged at the end.

Your part: pricing, in app/pricing.py. Build the API that prices an order (a list of agent and hours lines, with an optional promo code) by business rules 1 to 6 in README.md, and returns the itemized quote: subtotal, volume discount, promo discount, tax, and total. Only edit app/pricing.py.

Your team coordinates through Midflight: project hirebot-7bf3, your task is T2. Your Midflight tools are connected; follow Midflight's instructions, and pass task_id T2 and project_id hirebot-7bf3 to its tools.

Build your first working version, commit it on your branch (git add, git commit), and finish with a two-line summary of what you built.
```

## 03. To t3 (p1)

```
You are one of five developers' AI agents building HireBot together (read README.md first). Each agent builds one part on its own git branch, in its own folder, at the same time; you can't see the others' work until everything is merged at the end.

Your part: bookings, in app/bookings.py. Build the API that books an order (priced by the pricing rules, reserving hours from each agent's weekly capacity and refusing the whole booking if an agent doesn't have enough left), returns a booking by its id, cancels a booking (giving its hours back), and tells how many hours an agent has left this week. Only edit app/bookings.py.

Your team coordinates through Midflight: project hirebot-7bf3, your task is T3. Your Midflight tools are connected; follow Midflight's instructions, and pass task_id T3 and project_id hirebot-7bf3 to its tools.

Build your first working version, commit it on your branch (git add, git commit), and finish with a two-line summary of what you built.
```

## 04. To t4 (p1)

```
You are one of five developers' AI agents building HireBot together (read README.md first). Each agent builds one part on its own git branch, in its own folder, at the same time; you can't see the others' work until everything is merged at the end.

Your part: reports, in app/reports.py. Build the API for the revenue report: what HireBot earned, how many bookings are confirmed and cancelled, and the hours booked per agent (confirmed bookings only). Only edit app/reports.py.

Your team coordinates through Midflight: project hirebot-7bf3, your task is T4. Your Midflight tools are connected; follow Midflight's instructions, and pass task_id T4 and project_id hirebot-7bf3 to its tools.

Build your first working version, commit it on your branch (git add, git commit), and finish with a two-line summary of what you built.
```

## 05. To t5 (p1)

```
You are one of five developers' AI agents building HireBot together (read README.md first). Each agent builds one part on its own git branch, in its own folder, at the same time; you can't see the others' work until everything is merged at the end.

Your part: the command line, in cli/hirebot.py. Build every command in the 'The command line' section of README.md, printing exactly the keys it lists. It talks to the API over HTTP (the address is in HIREBOT_URL); use only Python's standard library or httpx. Only edit cli/hirebot.py.

Your team coordinates through Midflight: project hirebot-7bf3, your task is T5. Your Midflight tools are connected; follow Midflight's instructions, and pass task_id T5 and project_id hirebot-7bf3 to its tools.

Build your first working version, commit it on your branch (git add, git commit), and finish with a two-line summary of what you built.
```

## 06. To t1 (p2)

```
Check in with Midflight first, then update your part as needed, commit, and finish with a two-line summary.
```

## 07. To t2 (p2)

```
Check in with Midflight first, then update your part as needed, commit, and finish with a two-line summary.
```

## 08. To t3 (p2)

```
Note from your developer: when a booking is cancelled, refund the customer in full. We keep nothing.

Check in with Midflight first, then update your part as needed, commit, and finish with a two-line summary.
```

## 09. To t4 (p2)

```
Note from your developer: a cancelled booking keeps a 20% cancellation fee, and the report counts that fee as revenue.

Check in with Midflight first, then update your part as needed, commit, and finish with a two-line summary.
```

## 10. To t5 (p2)

```
Check in with Midflight first, then update your part as needed, commit, and finish with a two-line summary.
```

## 11. To t3 (say1792227657)

```
The lead decided the escalation. Check in with Midflight, then update your part as needed, commit, and finish with a two-line summary.
```

## 12. To t4 (say1792227785)

```
The lead decided the escalation. Check in with Midflight, then update your part as needed, commit, and finish with a two-line summary.
```

## 13. To fixer (fix1)

```
You are fixing a product after its parts, built separately by different AI agents, were merged (read README.md). Make the app work as a whole. These checks fail: (C7) booking an order. Ran: book meeting-ghost=10 rubber-duck=25 --promo BEEPBOOP. Expected: a booking id, status confirmed, total 2538. Got: error: 1 validation error for OrderLine
  Input should be a valid dictionary or instance of OrderLine [type=model_type, input_value=OrderLine(agent='meeting-ghost', hours=10.0), input_type=OrderLine]
    For further information visit https://errors.pydantic.dev/2.14/v/model_type (C8) show returns the booking. Ran: show <booking id>. Expected: status confirmed, total 2538. Got: error: unknown booking: missing (C9) booking reserves hours. Ran: availability meeting-ghost; availability rubber-duck. Expected: available 20, then available 55. Got: available: 30.0 | available: 80.0 (C11) cancelling a booking. Ran: cancel <booking id>; show <booking id>. Expected: status cancelled both times. Got: error: unknown booking: missing | error: unknown booking: missing (C13) the revenue report, with the cancellation fee the lead decided. Ran: book lgtm=5; report. Expected: revenue 686 (432 + a 10% fee of 254), confirmed 1, cancelled 1, hours: lgtm=5 only. Got: error: 1 validation error for OrderLine
  Input should be a valid dictionary or instance of OrderLine [type=model_type, input_value=OrderLine(agent='lgtm', hours=5.0), input_type=OrderLine]
    For further information visit https://errors.pydantic.dev/2.14/v/model_type | revenue: 0
confirmed: 0
cancelled: 0 (C14) a half-hour booking reserves half hours (plan change). Ran: book meeting-ghost=2.5; availability meeting-ghost. Expected: status confirmed, total 405, then available 27.5. Got: error: 1 validation error for OrderLine
  Input should be a valid dictionary or instance of OrderLine [type=model_type, input_value=OrderLine(agent='meeting-ghost', hours=2.5), input_type=OrderLine]
    For further information visit https://errors.pydantic.dev/2.14/v/model_type | available: 30.0 Commit when done; two-line summary.
```
