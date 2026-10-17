# Scale benchmark: 2 to 64 agents

Run on October 17, 2026 with [`scale_benchmark.py`](scale_benchmark.py), on `main` at
2d64b9b, on one MacBook (FalkorDB 4.22.1 in Docker from `compose.graph-hacks.yml`).
Every number is the median of 3 runs; "(max)" is the worst run. Raw numbers:
[`scale-results.json`](scale-results.json).

## What it does

No model and no tokens. Every agent is a thread that calls the services directly, as the
server's request handlers do. The plan is chains of four tasks (T1 provides `c1` to T2,
T2 provides `c2` to T3, T3 provides `c3` to T4, then a new chain starts). Each run:

1. **Claims at once.** Every agent submits its claim. Either all at the same instant, or
   at random moments over 5 seconds.
2. **Drift.** In every other chain the second task reads a field `total` where the
   contract says `amount`. These planted mismatches should be stopped, and nothing else.
3. **Check-in.** Every agent checks in once; the size of the reply text it would read.
4. **A plan change.** The lead adds a field to `c1`. Which tasks get a directive.

Five setups:

| Setup | What it stands for |
| --- | --- |
| memory, reviews inline | `uv run midflight-server` with no AI reviewer: the review runs inside the request |
| memory, reviews inline, 0.5 s reviewer, claims over 5 s | The same with a reviewer as slow as a model call (Nova 2 Lite took 2.5 s per review in [results.md](results.md)) |
| FalkorDB, one worker | The Graph Hacks server: one `RecoverableWorker` thread runs every review |
| FalkorDB, concurrent reviews | Reviews running side by side, as several worker Lambdas would |
| FalkorDB, one worker, 0.5 s reviewer, claims over 5 s | The Graph Hacks server with a reviewer as slow as a model call |

The reviewer is a stand-in that waits and finds nothing, so the only stops come from the
rules. "Gave up" is a review job that failed after its 3 runs (`MAX_REVIEW_RUNS`), because
other changes kept moving the project's `coord_rev` before it could save. Its claim stays
pending; it is never approved by accident (INV-03).

## Results

#### memory, reviews inline (local server)

| Agents | Claims wall (s) | p50 / p95 per claim (ms) | Approved | Stopped | Gave up (max) | Conflicts | Drift caught | False alarms | Check-in chars | Approve change (ms) | Got a directive |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | 0.00 | 0 / 0 | 1 | 1 | 0 (0) | 0 | 1 of 1 | 0 | 900 | 0 | T1, T2 |
| 4 | 0.00 | 0 / 0 | 3 | 1 | 0 (0) | 0 | 1 of 1 | 0 | 875 | 1 | T1, T2 |
| 8 | 0.00 | 0 / 1 | 7 | 1 | 0 (0) | 0 | 1 of 1 | 0 | 853 | 1 | T1, T2 |
| 16 | 0.00 | 0 / 0 | 14 | 2 | 0 (0) | 0 | 2 of 2 | 0 | 856 | 1 | T1, T2 |
| 32 | 0.01 | 0 / 0 | 28 | 4 | 0 (0) | 0 | 4 of 4 | 0 | 858 | 2 | T1, T2 |
| 64 | 0.01 | 0 / 1 | 56 | 8 | 0 (0) | 0 | 8 of 8 | 0 | 860 | 3 | T1, T2 |


#### memory, reviews inline, 0.5s reviewer, claims over 5.0s

| Agents | Claims wall (s) | p50 / p95 per claim (ms) | Approved | Stopped | Gave up (max) | Conflicts | Drift caught | False alarms | Check-in chars | Approve change (ms) | Got a directive |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | 1.64 | 1 / 504 | 1 | 1 | 0 (0) | 0 | 1 of 1 | 0 | 900 | 1 | T1, T2 |
| 4 | 4.63 | 511 / 511 | 3 | 1 | 0 (0) | 0 | 1 of 1 | 0 | 875 | 1 | T1, T2 |
| 8 | 5.02 | 511 / 1529 | 4 | 1 | 3 (3) | 9 | 1 of 1 | 0 | 834 | 1 | T1, T2 |
| 16 | 5.45 | 1523 / 1528 | 4 | 2 | 10 (10) | 30 | 2 of 2 | 0 | 824 | 2 | T1, T2 |
| 32 | 6.37 | 1524 / 1529 | 3 | 4 | 25 (25) | 79 | 4 of 4 | 0 | 819 | 3 | T1, T2 |


#### FalkorDB, one worker (Graph Hacks server)

| Agents | Claims wall (s) | p50 / p95 per claim (ms) | Approved | Stopped | Gave up (max) | Conflicts | Drift caught | False alarms | Check-in chars | Approve change (ms) | Got a directive |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | 0.04 | 9 / 10 | 1 | 1 | 0 (0) | 0 | 1 of 1 | 0 | 900 | 29 | T1, T2 |
| 4 | 0.08 | 16 / 16 | 3 | 1 | 0 (0) | 0 | 1 of 1 | 0 | 875 | 45 | T1, T2, T3, T4 |
| 8 | 0.11 | 22 / 25 | 7 | 1 | 0 (0) | 0 | 1 of 1 | 0 | 853 | 47 | T1, T2, T3, T4 |
| 16 | 0.24 | 55 / 62 | 14 | 2 | 0 (0) | 0 | 2 of 2 | 0 | 856 | 49 | T1, T2, T3, T4 |
| 32 | 0.49 | 90 / 109 | 28 | 4 | 0 (0) | 1 | 4 of 4 | 0 | 858 | 50 | T1, T2, T3, T4 |
| 64 | 0.99 | 182 / 212 | 56 | 8 | 0 (0) | 2 | 8 of 8 | 0 | 860 | 77 | T1, T2, T3, T4 |


#### FalkorDB, concurrent reviews (like many Lambda workers)

| Agents | Claims wall (s) | p50 / p95 per claim (ms) | Approved | Stopped | Gave up (max) | Conflicts | Drift caught | False alarms | Check-in chars | Approve change (ms) | Got a directive |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | 0.03 | 17 / 25 | 1 | 1 | 0 (0) | 1 | 1 of 1 | 0 | 900 | 36 | T1, T2 |
| 4 | 0.05 | 42 / 45 | 2 | 1 | 1 (1) | 6 | 1 of 1 | 0 | 862 | 53 | T1, T2, T3, T4 |
| 8 | 0.09 | 83 / 87 | 3 | 0 | 5 (5) | 18 | 0 of 1 | 0 | 798 | 46 | T1, T2, T3, T4 |
| 16 | 0.16 | 143 / 155 | 2 | 1 | 13 (13) | 43 | 1 of 2 | 0 | 803 | 35 | T1, T2, T3, T4 |
| 32 | 0.33 | 294 / 314 | 2 | 1 | 29 (29) | 91 | 1 of 4 | 0 | 795 | 39 | T1, T2, T3, T4 |
| 64 | 0.80 | 716 / 781 | 2 | 2 | 60 (60) | 186 | 2 of 8 | 0 | 796 | 53 | T1, T2, T3, T4 |


#### FalkorDB, one worker, 0.5s reviewer, claims over 5.0s

| Agents | Claims wall (s) | p50 / p95 per claim (ms) | Approved | Stopped | Gave up (max) | Conflicts | Drift caught | False alarms | Check-in chars | Approve change (ms) | Got a directive |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | 1.67 | 18 / 26 | 1 | 1 | 0 (0) | 0 | 1 of 1 | 0 | 900 | 34 | T1, T2 |
| 4 | 4.69 | 20 / 23 | 3 | 1 | 0 (0) | 0 | 1 of 1 | 0 | 875 | 51 | T1, T2, T3, T4 |
| 8 | 6.91 | 19 / 28 | 7 | 1 | 0 (1) | 4 | 1 of 1 | 0 | 853 | 50 | T1, T2, T3, T4 |
| 16 | 10.77 | 21 / 28 | 12 | 2 | 2 (2) | 7 | 2 of 2 | 0 | 849 | 49 | T1, T2, T3, T4 |
| 32 | 18.86 | 18 / 28 | 26 | 4 | 2 (3) | 9 | 4 of 4 | 0 | 855 | 60 | T1, T2, T3, T4 |

## What it says

- **Catching drift is reliable when the review finishes.** Every planted mismatch whose
  review completed was stopped, in every setup and size, and nothing else was ever
  stopped: 0 false alarms in 84 runs. The rules alone catch a renamed field.
- **Reviews that run side by side fail as the team grows.** With concurrent reviews the
  number of approved claims stays at 2 to 4 whatever the team size; at 64 agents 60 of 64
  reviews gave up. The same happens on the local server once the reviewer is as slow as
  a model: 3 or 4 approved at 8, 16, or 32 agents. Planted drift was then missed because
  its review gave up, not because the verdict was wrong.
- **One worker holds up much better, but not completely.** With a slow reviewer and claims
  arriving over 5 seconds, 2 reviews of 16, and 2 to 3 of 32, still gave up. With instant
  reviews nothing gave up up to 64 agents; a burst of 64 claims took about 1 second to
  review.
- **The cause is one counter for the whole project.** Every claim bumps `coord_rev`, and a
  review only saves if `coord_rev` hasn't moved since it started (INV-02). Any claim
  anywhere in the project, even an unrelated one, restarts every review in flight. A slow
  review is the one most likely to be overtaken.
- **The graph walk is right at every size.** The change to `c1` reached exactly T1 to T4
  (the whole first chain) on FalkorDB, and T1 and T2 with the direct rule on memory, the
  same in every run from 4 to 64 agents. Approving took 30 to 80 ms on FalkorDB.
- **Check-in replies don't grow with the team.** About 800 to 900 characters at 2 and at 64
  agents, because an agent is only told about its own task's neighbours.

## After the fixes

Run on October 17, 2026 on four commits: \`main\` and each of the three fix branches
stacked on it (\`scale-1-reuse-findings\`, \`scale-2-requeue-reviews\`,
\`scale-3-serialize-inline-reviews\`), with the same benchmark (d6996aa, which gives the
concurrent setup its own lock-free runner and adds a sixth setup: concurrent reviews with a
slow reviewer). Medians of 3 runs. Raw numbers: [\`scale-fixes.json\`](scale-fixes.json).
Each column includes the fixes to its left. Planted drift is not shown: every review that
finished stopped it, with 0 false alarms in every run on every commit.

#### memory, reviews inline (local server)

| Agents | main | + reuse the answer | + backoff and requeue | + one at a time |
| --- | --- | --- | --- | --- |
| 2 | 1 approved, 0 gave up | 1 approved, 0 gave up | 1 approved, 0 gave up | 1 approved, 0 gave up |
| 4 | 3 approved, 0 gave up | 3 approved, 0 gave up | 3 approved, 0 gave up | 3 approved, 0 gave up |
| 8 | 7 approved, 0 gave up | 7 approved, 0 gave up | 7 approved, 0 gave up | 7 approved, 0 gave up |
| 16 | 14 approved, 0 gave up | 14 approved, 0 gave up | 14 approved, 0 gave up | 14 approved, 0 gave up |
| 32 | 28 approved, 0 gave up | 28 approved, 0 gave up | 28 approved, 0 gave up | 28 approved, 0 gave up |
| 64 | 56 approved, 0 gave up | 56 approved, 0 gave up | 56 approved, 0 gave up | 56 approved, 0 gave up |

#### memory, reviews inline, 0.5s reviewer, claims over 5.0s

| Agents | main | + reuse the answer | + backoff and requeue | + one at a time |
| --- | --- | --- | --- | --- |
| 2 | 1 approved, 0 gave up | 1 approved, 0 gave up | 1 approved, 0 gave up | 1 approved, 0 gave up |
| 4 | 3 approved, 0 gave up | 3 approved, 0 gave up | 3 approved, 0 gave up | 3 approved, 0 gave up |
| 8 | 5 approved, 2 gave up | 7 approved, 0 gave up | 7 approved, 0 gave up | 7 approved, 0 gave up |
| 16 | 4 approved, 10 gave up | 14 approved, 0 gave up | 14 approved, 0 gave up | 14 approved, 0 gave up |
| 32 | 3 approved, 25 gave up | 26 approved, 2 gave up | 28 approved, 0 gave up | 28 approved, 0 gave up |

#### FalkorDB, one worker (Graph Hacks server)

| Agents | main | + reuse the answer | + backoff and requeue | + one at a time |
| --- | --- | --- | --- | --- |
| 2 | 1 approved, 0 gave up | 1 approved, 0 gave up | 1 approved, 0 gave up | 1 approved, 0 gave up |
| 4 | 3 approved, 0 gave up | 3 approved, 0 gave up | 3 approved, 0 gave up | 3 approved, 0 gave up |
| 8 | 7 approved, 0 gave up | 7 approved, 0 gave up | 7 approved, 0 gave up | 7 approved, 0 gave up |
| 16 | 14 approved, 0 gave up | 14 approved, 0 gave up | 14 approved, 0 gave up | 14 approved, 0 gave up |
| 32 | 28 approved, 0 gave up | 28 approved, 0 gave up | 28 approved, 0 gave up | 28 approved, 0 gave up |
| 64 | 56 approved, 0 gave up | 56 approved, 0 gave up | 56 approved, 0 gave up | 56 approved, 0 gave up |

#### FalkorDB, concurrent reviews (like many Lambda workers)

| Agents | main | + reuse the answer | + backoff and requeue | + one at a time |
| --- | --- | --- | --- | --- |
| 2 | 1 approved, 0 gave up | 1 approved, 0 gave up | 1 approved, 0 gave up | 1 approved, 0 gave up |
| 4 | 2 approved, 1 gave up | 3 approved, 0 gave up | 3 approved, 0 gave up | 3 approved, 0 gave up |
| 8 | 3 approved, 5 gave up | 7 approved, 0 gave up | 7 approved, 0 gave up | 7 approved, 0 gave up |
| 16 | 2 approved, 13 gave up | 8 approved, 6 gave up | 14 approved, 0 gave up | 14 approved, 0 gave up |
| 32 | 1 approved, 29 gave up | 9 approved, 20 gave up | 28 approved, 0 gave up | 28 approved, 0 gave up |
| 64 | 2 approved, 60 gave up | 9 approved, 50 gave up | 55 approved, 1 gave up | 54 approved, 2 gave up |

#### FalkorDB, one worker, 0.5s reviewer, claims over 5.0s

| Agents | main | + reuse the answer | + backoff and requeue | + one at a time |
| --- | --- | --- | --- | --- |
| 2 | 1 approved, 0 gave up | 1 approved, 0 gave up | 1 approved, 0 gave up | 1 approved, 0 gave up |
| 4 | 3 approved, 0 gave up | 3 approved, 0 gave up | 3 approved, 0 gave up | 3 approved, 0 gave up |
| 8 | 7 approved, 0 gave up | 7 approved, 0 gave up | 7 approved, 0 gave up | 7 approved, 0 gave up |
| 16 | 12 approved, 2 gave up | 14 approved, 0 gave up | 14 approved, 0 gave up | 14 approved, 0 gave up |
| 32 | 26 approved, 2 gave up | 28 approved, 0 gave up | 28 approved, 0 gave up | 28 approved, 0 gave up |

#### FalkorDB, concurrent reviews, 0.5s reviewer, claims over 5.0s

| Agents | main | + reuse the answer | + backoff and requeue | + one at a time |
| --- | --- | --- | --- | --- |
| 2 | 1 approved, 0 gave up | 1 approved, 0 gave up | 1 approved, 0 gave up | 1 approved, 0 gave up |
| 4 | 3 approved, 0 gave up | 3 approved, 0 gave up | 3 approved, 0 gave up | 3 approved, 0 gave up |
| 8 | 4 approved, 3 gave up | 7 approved, 0 gave up | 7 approved, 0 gave up | 7 approved, 0 gave up |
| 16 | 4 approved, 10 gave up | 14 approved, 0 gave up | 14 approved, 0 gave up | 14 approved, 0 gave up |
| 32 | 3 approved, 25 gave up | 20 approved, 8 gave up | 28 approved, 0 gave up | 28 approved, 0 gave up |

### Model calls and waiting, local server, 0.5 s reviewer, claims over 5 s

The third fix doesn't change what gets approved in this benchmark; the second already
gets every review through. What it changes is how often the reviewer is asked and how
long a claim waits. Medians of 3 runs, counted with [`scale_calls.py`](scale_calls.py):

| Agents | Reviewer calls, + backoff and requeue | Reviewer calls, + one at a time | Wait per claim (median), + backoff and requeue | + one at a time |
| --- | --- | --- | --- | --- |
| 8 | 10 | 11 | 0.5 s | 2.4 s |
| 16 | 55 | 21 | 1.6 s | 5.4 s |
| 32 | 130 | 36 | 2.2 s | 10.0 s |

With reviews side by side, each one is overtaken by claims joining the set it compares
against, so its input changes and the model is asked again: 130 calls for 28 reviews at 32
agents. One at a time, each review is asked about once, at the price of claims queueing
behind each other. On a real model that is a cost-against-latency choice.

### What changed

- **Reusing the reviewer's answer** fixed every setup where the reviewer is slow and only
  one thing reviews at a time: on the Graph Hacks worker nothing gave up at any size. It
  also cut the local server's give-ups at 32 agents from 25 to 2.
- **Backoff and requeue** fixed reviews running side by side: at 32 agents 28 approved and
  0 gave up, against 1 approved and 29 gave up on \`main\`. At 64 agents with instant
  reviews, 1 or 2 of 64 still gave up; that setup has no worker to requeue them.
- **One at a time** made the local server ask the reviewer 3.6 times less at 32 agents,
  and made each claim wait about 4 times longer.

## Limits of this benchmark

- It runs on one machine with threads, not separate processes or the AWS deployment.
  DynamoDB was not measured. Its worker Lambda reads the stream one record at a time per
  shard (`BatchSize: 1`, no parallelization factor in `infra/template.yaml`), so a small
  table behaves closer to "one worker" than to "concurrent reviews".
- The reviewer is a stand-in. Real model reviews also add findings, so a real run would
  stop more claims; this measures only how the coordination holds up.
- The plan shape (chains of four) keeps each task's neighbourhood small. A plan where one
  contract has many consumers would give larger check-ins and wider plan changes.

## The fixes

Made in three stacked branches, measured above: D35 (reuse the reviewer's answer when its
input is unchanged), D36 (random backoff between reruns, requeue on the worker), and D37
(inline jobs one at a time per project).
