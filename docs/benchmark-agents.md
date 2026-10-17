# Agent benchmark: 2, 5, and 6 agents, October 17, 2026

Seventeen trials of real coding agents building a product together, run unattended
overnight on one MacBook: three cases of rising size, each with three ways to coordinate.
Every agent is a headless Claude Code session (`claude -p`, the `sonnet` alias of that
day) that reads the repository, writes code, runs it, commits, and calls its tools for up
to 50 turns per message. The results folders hold every prompt, every reply, and every
check: `experiment/cases/<case>/results/<run>/`.

## What ran

| Case | Agents | Phases | What happens after the plan is written | Checks |
| --- | --- | --- | --- | --- |
| [Tabby](../experiment/cases/tabby/README.md) (new) | 2 | 3 | a plan change, two developers who disagree, a note against the plan | 9 |
| [HireBot Pro](../experiment/cases/hirebot-pro/README.md) | 5 | 2 | a plan change touching four parts, two developers who disagree | 14 |
| [PigeonPost](../experiment/cases/pigeonpost/README.md) | 6 | 4 | six events, separate laptops, agents starting at different times | 20 |

| Run letter | How the agents coordinate |
| --- | --- |
| **N** | They can't. Each agent only hears from its own developer. |
| **A** | A team chat file every agent and the lead can read and write. |
| **B** | Midflight: claims, check-ins, directives, escalations to the lead. |

**Midflight** in every B run except B6 is the version with the three scale fixes (#12 to
#14, commit 7227a92 or 9c0a55d), served on the same machine by
`experiment/local_midflight.py`: everything in memory, one person signed in who leads and
owns every task. **The reviewer** was a real model in Tabby B1 to B3, HireBot Pro B8, and
PigeonPost B3: Claude Haiku through the Claude Code CLI (`experiment/claude_reviewer.py`),
with Midflight's own prompts and second look, because this machine has no AWS credentials
for Nova. HireBot Pro B6 and B7 used the case's scripted reviewer. B6 ran on `main` before
the fixes. **The lead** is scripted with a decision sheet fixed before any trial
(`experiment/matrix.py`, and each case's `case.py`). **Scoring** merges every branch, runs
the checks, then gives failing checks to a fixer agent for up to three rounds.

## Results

Checks passing at merge, before any fix round. "Events held" counts the mid-flight events
whose checks all passed (PigeonPost and Tabby only). Every run reached all checks after
at most one fix round. Cost is what the Claude Code CLI reports for the agents, the lead,
and the fixer; the reviewer's cost is listed separately.

### Tabby (2 agents)

| Run | Approach | At merge | Events held | Failed | Cost | Turns | Minutes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| N1 | no channel | 6 of 9 | 1 of 3 | C7, C8, C9 | $3.35 | 178 | 10 |
| N2 | no channel | 6 of 9 | 1 of 3 | C7, C8, C9 | $2.30 | 111 | 8 |
| N3 | no channel | 6 of 9 | 1 of 3 | C7, C8, C9 | $2.55 | 125 | 9 |
| A1 | team chat | 2 of 9 | 0 of 3 | C1, C2, C5 to C9 | $3.23 | 177 | 10 |
| A2 | team chat | 7 of 9 | 1 of 3 | C5, C7 | $2.63 | 135 | 8 |
| A3 | team chat | **9 of 9** | 3 of 3 | none | $1.97 | 98 | 6 |
| B1 | Midflight | 6 of 9 | 1 of 3 | C7, C8, C9 | $2.83 | 152 | 14 |
| B2 | Midflight | 7 of 9 | 2 of 3 | C7, C8 | $2.47 | 136 | 12 |
| B3 | Midflight | 6 of 9 | 1 of 3 | C7, C8, C9 | $2.79 | 134 | 15 |

Reviewer (Haiku): 26, 13, and 28 calls; $0.28, $0.15, $0.27.

### HireBot Pro (5 agents)

| Run | Approach | At merge | Failed | Cost | Turns | Minutes |
| --- | --- | --- | --- | --- | --- | --- |
| N2 | no channel | 8 of 14 | C7 to C9, C11, C13, C14 | $6.09 | 250 | 15 |
| A2 | team chat | **14 of 14** | none | $8.07 | 276 | 16 |
| B6 | Midflight (`main`, scripted reviewer) | 13 of 14 | C13 | $7.44 | 283 | 37 |
| B7 | Midflight (scripted reviewer) | 8 of 14 | C7 to C9, C11, C13, C14 | $6.46 | 262 | 17 |
| B8 | Midflight (Haiku reviewer) | 13 of 14 | C13 | $7.23 | 299 | 20 |

Reviewer in B8: 31 calls, $0.61. For comparison, the runs of October 10 and 11 on the
model of that day: N1 13, A1 14, B1 to B4 13 to 14 of 14, at $1.17 to $2.68 each.

### PigeonPost (6 agents)

| Run | Approach | At merge | Events held | Failed | Cost | Turns | Minutes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| N2 | no channel | 15 of 20 | 4 of 6 | C9, C11, C18 to C20 | $7.96 | 323 | 13 |
| A2 | team chat | **20 of 20** | 6 of 6 | none | $7.35 | 297 | 20 |
| B3 | Midflight (Haiku reviewer) | 17 of 20 | 4 of 6 | C9, C10, C11 | $8.96 | 341 | 28 |

Reviewer in B3: 24 calls, $0.45. Earlier runs on the live service: N1 13, A1 18, B1 and B2
20 of 20.

## What it says

**With the current model, Midflight didn't beat a team chat on any case.** The chat
reached every check at merge once per case (Tabby A3, HireBot Pro A2, PigeonPost A2);
no Midflight run did. On Tabby the three Midflight runs scored like no channel at all
(6, 7, 6 against 6, 6, 6), and the chat varied the most (2, 7, 9). One run per approach
on the larger cases is not enough to rank them; the failures below are the useful part.

**1. The most common failure is a seam no contract covers.** Four HireBot Pro runs (N2,
B6, B7, B8, with and without Midflight) failed because one part handed another Python
objects where the other expected dicts, or a model class from its own module. In B7 the
agents agreed through Midflight on `price_order(items, promo_code, rush)`, recorded as a
decision, without saying what `items` holds; bookings passed its own `OrderLine` objects
and pricing's model rejected them, which broke six checks. PigeonPost's report failed on the
same kind of seam in B3 (C10): billing read `dispatch.deliveries`, while dispatch kept its
deliveries in `dispatch._deliveries`. Midflight's contracts describe JSON fields; these
parts call each other in-process, and nothing pins down names, argument types, or return
types there.

**2. Midflight settled product questions itself.** Tabby's two developers wanted
different default tips (18% and 15%); the plan is silent, and the lead's sheet says 20%.
In all three Midflight runs the question never reached the lead: Midflight recorded it as
agreed between the tasks (B1) or decided it as a technical question (B3), and the
default tip failed every time (C7, C8). In B1 and B3 it also recorded the API's half-up
rounding as agreed, though R-2 says rounded up (C9). A default amount the customer pays is
a product decision (D32), and an agreement that contradicts a plan requirement shouldn't
be possible.

**3. Escalations raised in the last phase go unanswered.** In Tabby B1 and PigeonPost B3
an agent opened an escalation in the final phase, after the lead's last turn, and merged
anyway. In a real team the pre-push hook would hold the push while the escalation is
open; the trials merge every branch without it.

**4. An agent can follow its own developer over the lead.** In PigeonPost B3 the lead
decided the cancellation fee through Midflight (25%), and dispatch then built a full
refund because its developer had said so, opening a second escalation (E-6) too late
(C9, C11).

**5. Midflight's own machinery held up.** No agent in any B run was told that a review
gave up, was incomplete, or was still running (searched in every agent's event log), and
the real conflicts in HireBot Pro (the cancellation fee) and PigeonPost (refund against
fee) went to the lead as product questions with both sides, and were decided once.

**6. The current model works about three times longer.** The same HireBot Pro case cost
$6 to $8 and took 250 to 300 turns, against $1 to $3 and 60 to 165 turns on October 10 and
11.

## Changes this points to

In order of how many failed checks they explain:

1. **In-process interfaces as contracts.** Let a contract describe a Python function
   (name, argument and return types, dict or object), or have the reviewer flag a provider
   and a consumer that disagree on the shape of a value they both name.
2. **Never agree or settle against the plan.** Before recording an agreement (D30) or a
   reviewer decision (D31), check it against the plan's requirements; a contradiction is a
   requirement conflict for the lead. Treat defaults, fees, and rounding of money as
   product questions.
3. **Hold the merge on open escalations.** Add the pre-push gate to the trials (merge only
   branches whose `ready_to_push` is true), and in the product, remind the lead of open
   escalations at the end of a phase.
4. **Restate a lead decision to the agent that ignores it.** When a claim revision
   contradicts a decision in force, the verdict should say so plainly instead of opening a
   new escalation.

## Limits

- One run per approach on HireBot Pro and PigeonPost, three on Tabby. Agent runs vary a
  lot (Tabby A: 2, 7, 9).
- The reviewer was Claude Haiku through the CLI, not Nova 2 Lite on Bedrock, and the
  Midflight was local, in memory, with one person owning every task, so agents had the
  lead's tools in view. The live service was not used.
- The lead is scripted from a fixed sheet and only acts at fixed points.

## Reproducing

```sh
uv sync --extra falkordb
python experiment/run.py tabby X selftest           # the reference build: 9 of 9
.venv/bin/python experiment/matrix.py tabby:B4:claude tabby:N4 tabby:A4
```

`matrix.py` starts a local Midflight for each B run, plays the lead, waits out usage
limits, and records each trial.
