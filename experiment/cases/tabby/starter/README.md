# Tabby

Tabby splits cafe bills. A waiter types the order into the command line; Tabby works out
the subtotal, the tip, and the total, and how much each person pays when a table splits
the bill.

Money is in dollars with two decimals.

## The parts

| Part | File | What it does |
| --- | --- | --- |
| Bills API | `app/bills.py` | Bills and splits, over HTTP |
| Command line | `cli/tabby.py` | What the waiter types |

`app/main.py` wires the API together; nobody needs to change it.

## The command line

`python -m cli.tabby <command>` talks to the API at the address in the `TABBY_URL`
environment variable (default `http://127.0.0.1:8000`). Every command prints `key: value`
lines, exactly these keys in this order. On any error it prints one line `error: <what went
wrong>` and exits with status 1.

| Command | Prints |
| --- | --- |
| `bill <name>:<price>:<qty> ... [--tip <percent>]` | `bill:` (the new id), `subtotal:`, `tip:`, `total:` |
| `show <id>` | `bill:`, `subtotal:`, `tip:`, `total:` |
| `split <id> --people <n>` | `per_person:` |

Example:

```
$ python -m cli.tabby bill coffee:3.50:2 bagel:4.25:1 --tip 18
bill: 1
subtotal: 11.25
tip: 2.03
total: 13.28
```

## Running it

```
uv run --with fastapi --with uvicorn --with httpx uvicorn app.main:app --port 8000
```
