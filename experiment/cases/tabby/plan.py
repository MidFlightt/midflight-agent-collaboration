"""Tabby's plan: the requirements, tasks, and contracts every approach starts from.

One source for three things, so no approach is told more than another:

- starter/PLAN.md, which every agent in every approach reads (`python plan.py` writes it);
- the plan the lead proposes in Midflight (run B): `plan(1, owner)`;
- the lead's launch change: `change_message()` for runs N and A, `plan(2, owner)` for B.
"""

from __future__ import annotations

import copy
from pathlib import Path

REQUIREMENTS = {
    "R-1": (
        "POST /bills creates a bill from its items (each a name, a price in dollars, and a "
        "quantity) and a tip_percent. Subtotal = sum of price x quantity. Tip = tip_percent "
        "% of the subtotal. Total = subtotal + tip. Money is in dollars with two decimals; "
        "round half up to the cent wherever a fraction of a cent appears. The reply is the "
        "bill with a new id. GET /bills/{id} returns a bill; an unknown id is a 404."
    ),
    "R-2": (
        "GET /bills/{id}/split?people=N splits a bill between N people (N from 1): "
        "per_person = total / N, rounded up to the next cent so the cafe is never short. An "
        "unknown bill is a 404."
    ),
    "R-3": (
        "The command line (cli/tabby.py) offers every command in README.md's 'The command "
        "line' section over HTTP and prints exactly the keys listed there."
    ),
}

# id: (title, file, branch, requirements, provides, consumes)
TASKS = {
    "T1": ("Bills API", "app/bills.py", "t1-bills", ["R-1", "R-2"],
           ["bill-request", "bill", "split"], []),
    "T2": ("Command line", "cli/tabby.py", "t2-cli", ["R-3"], [],
           ["bill-request", "bill", "split"]),
}  # fmt: skip

# id: (provider, consumers, fields)
CONTRACTS = {
    "bill-request": ("T1", ["T2"], {"items": "array", "tip_percent": "number"}),
    "bill": ("T1", ["T2"], {
        "id": "integer", "subtotal": "number", "tip": "number", "total": "number"}),
    "split": ("T1", ["T2"], {"bill": "integer", "people": "integer", "per_person": "number"}),
}  # fmt: skip

# The lead's launch change (plan version 2): a service charge. ---------------------------

SERVICE = (
    "Service charge. Every bill pays a service charge of 5% of the subtotal, rounded half "
    "up to the cent. The tip is still a percentage of the subtotal only. Total = subtotal "
    "+ service + tip. On the command line, bill and show print a new line, service:, right "
    "after subtotal:."
)
SERVICE_TASKS = ["T1", "T2"]
SERVICE_FIELDS = {"bill": {"service": "number"}}
CHANGE_REASON = "Launch change: service charge"


def tables(version: int) -> tuple[dict, dict, dict]:
    requirements = dict(REQUIREMENTS)
    tasks = copy.deepcopy(TASKS)
    contracts = copy.deepcopy(CONTRACTS)
    if version >= 2:
        requirements["R-4"] = SERVICE
        for task in SERVICE_TASKS:
            tasks[task][3].append("R-4")
        for contract, fields in SERVICE_FIELDS.items():
            contracts[contract][2].update(fields)
    return requirements, tasks, contracts


def plan(version: int, owner: str) -> dict:
    """The plan as Midflight's propose_plan takes it; `owner` owns every task."""
    requirements, tasks, contracts = tables(version)
    return {
        "requirements": [{"id": i, "description": text} for i, text in requirements.items()],
        "tasks": [
            {"id": i, "title": f"{title} ({file})", "owner": owner, "branch": branch,
             "requirement_ids": reqs, "provides": provides, "consumes": consumes}
            for i, (title, file, branch, reqs, provides, consumes) in tasks.items()
        ],
        "contracts": [
            {"id": i, "provider_task": provider, "consumer_tasks": consumers, "fields": fields}
            for i, (provider, consumers, fields) in contracts.items()
        ],
    }  # fmt: skip


def render(version: int = 1) -> str:
    requirements, tasks, contracts = tables(version)
    return "\n".join([
        f"# Tabby: the plan (version {version})",
        "",
        "The lead wrote this plan before anyone started. README.md describes the product;",
        "this page says who builds what and what the parts hand each other.",
        "",
        "## Requirements",
        "",
        "| Id | Requirement |",
        "| --- | --- |",
        *(f"| {i} | {text} |" for i, text in requirements.items()),
        "",
        "## Tasks",
        "",
        "One developer, with their AI agent, per task. Each task edits only its file.",
        "",
        "| Task | Part | File | Requirements | Provides | Consumes |",
        "| --- | --- | --- | --- | --- | --- |",
        *(
            f"| {i} | {title} | `{file}` | {', '.join(reqs)} | "
            f"{names(provides)} | {names(consumes)} |"
            for i, (title, file, _, reqs, provides, consumes) in tasks.items()
        ),
        "",
        "## Contracts",
        "",
        "What one part hands another, as JSON. Field names and types are exact. An item in",
        "`items` is an object with `name` (string), `price` (number), and `qty` (integer).",
        "",
        "| Contract | From | To | Fields |",
        "| --- | --- | --- | --- |",
        *(
            f"| `{i}` | {provider} | {', '.join(consumers)} | "
            f"{', '.join(f'`{name}`: {kind}' for name, kind in fields.items())} |"
            for i, (provider, consumers, fields) in contracts.items()
        ),
        "",
    ])  # fmt: skip


def change_message() -> str:
    fields = "; ".join(
        f"`{contract}` gains " + ", ".join(f"`{name}`: {kind}" for name, kind in added.items())
        for contract, added in SERVICE_FIELDS.items()
    )
    return (
        f"One change for launch, a new requirement R-4. {SERVICE} Contracts: {fields}. "
        "It concerns the bills API (T1) and the command line (T2)."
    )


def names(contracts: list[str]) -> str:
    return ", ".join(f"`{c}`" for c in contracts) or "none"


if __name__ == "__main__":
    target = Path(__file__).resolve().parent / "starter" / "PLAN.md"
    target.write_text(render(1), encoding="utf-8", newline="\n")
    print(f"wrote {target}")
