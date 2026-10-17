# Tabby: the plan (version 1)

The lead wrote this plan before anyone started. README.md describes the product;
this page says who builds what and what the parts hand each other.

## Requirements

| Id | Requirement |
| --- | --- |
| R-1 | POST /bills creates a bill from its items (each a name, a price in dollars, and a quantity) and a tip_percent. Subtotal = sum of price x quantity. Tip = tip_percent % of the subtotal. Total = subtotal + tip. Money is in dollars with two decimals; round half up to the cent wherever a fraction of a cent appears. The reply is the bill with a new id. GET /bills/{id} returns a bill; an unknown id is a 404. |
| R-2 | GET /bills/{id}/split?people=N splits a bill between N people (N from 1): per_person = total / N, rounded up to the next cent so the cafe is never short. An unknown bill is a 404. |
| R-3 | The command line (cli/tabby.py) offers every command in README.md's 'The command line' section over HTTP and prints exactly the keys listed there. |

## Tasks

One developer, with their AI agent, per task. Each task edits only its file.

| Task | Part | File | Requirements | Provides | Consumes |
| --- | --- | --- | --- | --- | --- |
| T1 | Bills API | `app/bills.py` | R-1, R-2 | `bill-request`, `bill`, `split` | none |
| T2 | Command line | `cli/tabby.py` | R-3 | none | `bill-request`, `bill`, `split` |

## Contracts

What one part hands another, as JSON. Field names and types are exact. An item in
`items` is an object with `name` (string), `price` (number), and `qty` (integer).

| Contract | From | To | Fields |
| --- | --- | --- | --- |
| `bill-request` | T1 | T2 | `items`: array, `tip_percent`: number |
| `bill` | T1 | T2 | `id`: integer, `subtotal`: number, `tip`: number, `total`: number |
| `split` | T1 | T2 | `bill`: integer, `people`: integer, `per_person`: number |
