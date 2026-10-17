"""Tabby: everything the agents and the lead say during a trial.

Two agents build one small product, each on its own copy of the repository: the bills
API and the command line that calls it. Every approach gets the same plan, task text,
developer notes, and number of turns; only the coordination line differs (N: nothing,
A: a CHAT.md team chat, B: Midflight). The lead is an agent with a decision sheet fixed
in advance; it answers what it is asked and never volunteers a decision.

The simple tier next to HireBot Pro (5 agents) and PigeonPost (6 agents, 4 phases).
"""

import importlib.util
import json
from pathlib import Path

_plan_file = Path(__file__).with_name("plan.py")
_spec = importlib.util.spec_from_file_location("tabby_plan", _plan_file)
plan = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(plan)

SEPARATE_LAPTOPS = True
PARALLEL = 2

BRANCHES = {agent.lower(): task[2] for agent, task in plan.TASKS.items()}

PHASES = {1: ["t1", "t2"], 2: ["t1", "t2"], 3: ["t1", "t2"]}

STEPS = [
    ("lead", "plan"),
    ("phase", 1),
    ("lead", "answer"),
    ("lead", "change"),
    ("phase", 2),
    ("lead", "answer"),
    ("phase", 3),
    ("merge",),
    ("repair",),
    ("record",),
]

INTRO = (
    "You are one of two developers' AI agents building Tabby together (read README.md "
    "and PLAN.md first). Each developer works on their own laptop, on their own git "
    "branch, at the same time. You can't see the other's code until everything is merged "
    "at the end."
)

TASKS = {
    "t1": (
        "Your part is T1, the bills API, in app/bills.py: requirements R-1 and R-2 and the "
        "`bill-request`, `bill`, and `split` contracts in PLAN.md. Only edit app/bills.py."
    ),
    "t2": (
        "Your part is T2, the command line, in cli/tabby.py: requirement R-3 and every "
        "command in README.md's 'The command line' section. Use only Python's standard "
        "library or httpx. Only edit cli/tabby.py."
    ),
}

# What each developer privately tells their own agent, and in which phase.
DEVELOPER_NOTE = {
    "t1": {
        1: (
            "Note from your developer: customers complain about paying an extra cent. Round "
            "the split per person half up, not up."
        ),
        2: (
            "Note from your developer: when a bill comes without tip_percent, use an 18% "
            "tip. That's our house rule."
        ),
    },
    "t2": {
        2: (
            "Note from your developer: when the waiter doesn't give --tip, send tip_percent "
            "15. That's what most tables leave."
        ),
    },
}

FIRST = (
    "Build your first working version, commit it on your branch (git add, git commit), "
    "and finish with a two-line summary of what you built."
)
UPDATE = "update your part as needed, commit, and finish with a two-line summary."
LAST_CALL = "Last call before everything is merged."
LOOK_FIRST = {
    "N": "",
    "A": "Read the team chat first, then ",
    "B": "Check in with Midflight first, then ",
}


def coordination(approach: str, agent: str, project: str | None) -> str:
    if approach == "N":
        return (
            "You have no way to talk to the other agent; tell your developer anything the "
            "team should know."
        )
    if approach == "A":
        return (
            "Team chat: the file CHAT.md on the `chat` branch of the team's GitHub "
            "repository. `python tools/chat.py read` prints it, and `python tools/chat.py "
            'post "<your part>: <message>"` adds a line. Read it before you start and '
            "before you finish; post a line if you want to tell or ask the team something. "
            "The lead reads it."
        )
    task = agent.upper()
    return (
        f"Your team coordinates through Midflight: project {project}, your task is {task}. "
        "Your Midflight tools are connected; follow Midflight's instructions, and pass "
        f"task_id {task} and project_id {project} to its tools."
    )


def prompt(approach: str, agent: str, phase: int, project: str | None) -> str:
    parts = []
    if phase == 1:
        parts += [INTRO, TASKS[agent], coordination(approach, agent, project)]
    if phase == 2 and approach == "N":
        parts.append("Message from the lead to the whole team: " + plan.change_message())
    note = DEVELOPER_NOTE.get(agent, {}).get(phase)
    if note:
        parts.append(note)
    if phase == 1:
        parts.append(FIRST)
    else:
        closing = sentence(LOOK_FIRST[approach] + UPDATE)
        parts.append(f"{LAST_CALL} {closing}" if phase == max(PHASES) else closing)
    return "\n\n".join(parts)


def sentence(text: str) -> str:
    return text[0].upper() + text[1:]


# The lead ------------------------------------------------------------------------------

# Neither developer says 20%, so that answer only exists if the question reaches the lead.
LEAD_DECISIONS = [
    (
        "Default tip",
        "A bill without tip_percent gets a 20% tip. The command line sends no tip_percent "
        "when the waiter gives no --tip.",
    ),
    (
        "Splitting",
        "The plan stands: the split per person is rounded up to the next cent, exactly as "
        "R-2 says.",
    ),
    (
        "Money and names",
        "The plan stands: money in dollars with two decimals, and field names exactly as in "
        "the contracts.",
    ),
]
NOT_ON_THE_SHEET = "Your call between the parts involved; keep to the plan."
SHEET = "\n".join(f"{n}. {topic}: {text}" for n, (topic, text) in enumerate(LEAD_DECISIONS, 1))

CHAT_TOOLS = ["Read", "Bash(python tools/chat.py:*)"]
MIDFLIGHT = "mcp__midflight-live__"
PLAN_TOOLS = [MIDFLIGHT + name for name in ("project_status", "propose_plan", "approve_plan")]
ANSWER_TOOLS = [MIDFLIGHT + name for name in ("project_status", "check_in", "resolve_escalation")]


def lead(approach: str, step: str, project: str | None) -> dict | None:
    if approach == "N":
        return None
    if step == "plan":
        return propose(1, "First plan", project) if approach == "B" else None
    if step == "change":
        if approach == "A":
            return {"post": "Lead: " + plan.change_message()}
        return propose(2, plan.CHANGE_REASON, project)
    if approach == "A":
        return {"tools": CHAT_TOOLS, "prompt": (
            "You are the lead of the Tabby team; README.md and PLAN.md are your plan. "
            "Your team's AI agents talk in the team chat: `python tools/chat.py read` prints "
            'it, and `python tools/chat.py post "Lead: <message>"` adds a line.\n\n'
            "Read the chat now. Post one answer for each question to the lead, and for each "
            "conflict someone has pointed out (between two parts, or between a part and the "
            "plan), that you haven't answered yet. Answer only from your decision sheet, "
            "word for word, and say who it is for. If nothing on the sheet settles it, "
            f'answer: "{NOT_ON_THE_SHEET}" Don\'t bring up a decision nobody asked for, and '
            "post nothing if nothing needs you.\n\n"
            f"Your decision sheet, fixed before the project started:\n{SHEET}\n\n"
            "Finish with one line: how many answers you posted."
        )}  # fmt: skip
    return {"tools": ANSWER_TOOLS, "prompt": (
        f"You are the lead of Midflight project {project} (pass project_id {project} to "
        "every tool). Call project_status. For each open escalation that is waiting for "
        "the lead, call resolve_escalation. If your decision sheet settles it, use "
        "resolution request_revision with the decision, word for word, as the reason. If "
        f'nothing on the sheet settles it, use request_revision with the reason "'
        f'{NOT_ON_THE_SHEET}" If it isn\'t a disagreement at all, dismiss it with a one-line '
        "reason. Don't change the plan, and don't act on anything that isn't an open "
        "escalation.\n\n"
        f"Your decision sheet, fixed before the project started:\n{SHEET}\n\n"
        "Finish with one line: how many escalations you decided."
    )}  # fmt: skip


def propose(version: int, reason: str, project: str | None) -> dict:
    draft = json.dumps(plan.plan(version, "OWNER"), indent=1)
    return {"tools": PLAN_TOOLS, "prompt": (
        f"You are the lead of Midflight project {project} (pass project_id {project} to "
        "every tool). Call project_status to find your own GitHub login: you are the lead. "
        "Then call propose_plan with exactly this plan, putting your login in place of "
        f"OWNER in every task:\n\n{draft}\n\n"
        f'Then call approve_plan with the version it returns and the reason "{reason}". '
        "Finish with one line: the plan version you approved."
    )}  # fmt: skip
