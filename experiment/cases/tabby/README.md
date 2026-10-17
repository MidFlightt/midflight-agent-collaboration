# Case: Tabby (2 agents)

The simple tier of the benchmark: two agents, three phases, 9 checks scored
automatically. Tabby splits cafe bills; T1 builds the bills API, T2 the command line
that calls it.

| File | What it is |
| --- | --- |
| `case.py` | Every word an agent or the lead is told, per approach and phase |
| `plan.py` | The plan (v1) and the lead's change (v2); writes `starter/PLAN.md` |
| `starter/` | The near-empty repository every trial starts from |
| `reference/` | A build that passes every check (`python experiment/run.py tabby X selftest`) |
| `checks.md`, `score.py` | The checks, fixed before any trial |
| `results/` | One folder per recorded trial |

The events are in `checks.md`. Run a whole trial with
`python experiment/run.py tabby <run> auto [project]`, or several with
`experiment/matrix.py`.
