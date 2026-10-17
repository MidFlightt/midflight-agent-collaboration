"""How Midflight holds up as a team grows: 2 to 64 agents claiming at the same moment.

No model and no tokens: the review is the rules only, and every agent is a thread calling
the services directly, the way the server's request handlers do. Each run builds a fresh
project whose plan is chains of four tasks (T1 provides c1 to T2, T2 provides c2 to T3,
and so on), then measures four things:

1. **Claims at once.** Every agent submits its claim at the same instant. The review runs
   in the same thread (InlineRunner), so reviews race on the project's `coord_rev`.
   Counted: approved, stopped, and reviews that gave up after their retries.
2. **Drift caught.** In every other chain the second task reads field `total` where the
   contract says `amount`. Every planted mismatch should be stopped and nothing else.
3. **Check-in size.** Every agent checks in once; the reply text an agent would read.
4. **A plan change.** The lead adds a field to `c1`. Counted: which tasks get a directive.
   The graph walk (FalkorDB) should reach the whole first chain; the direct rule (memory)
   only the provider and the consumer of `c1`.

    uv run python evals/scale_benchmark.py                          # memory
    uv run --extra falkordb python evals/scale_benchmark.py --falkordb  # both

`--falkordb` needs the Graph Hacks database on 127.0.0.1:6379
(`docker compose -f compose.graph-hacks.yml up -d`). Each run uses its own graph and
deletes it afterwards. Results: evals/scale-results.md.
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
import threading
import time
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

from midflight.adapters.clock import SystemClock
from midflight.adapters.memory_store import MemoryStore
from midflight.adapters.worker import RecoverableWorker
from midflight.api.app import build_services
from midflight.api.views import check_in_json
from midflight.domain.models import (
    ClaimState,
    Contract,
    FieldType,
    InterfaceUse,
    JobKind,
    JobState,
    Participant,
    Plan,
    PlanStatus,
    Project,
    Requirement,
    Role,
    Task,
)
from midflight.mcp.replies import check_in_text
from midflight.ports import Commit, RevisionConflict, Store
from midflight.services.claims import ClaimSubmission
from midflight.services.plans import PlanDraft

PROJECT = "bench"
LEAD = "p-lead"
CHAIN = 4
SIZES = [2, 4, 8, 16, 32, 64]
STOPPED = {ClaimState.NEEDS_REVISION, ClaimState.HUMAN_REVIEW_REQUIRED}


class Counting:
    """Mixed into the real store class: counts commits refused because coord_rev moved
    (INV-02). A subclass, not a wrapper, so `isinstance(store, GraphPlanStore)` still
    sees the graph methods."""

    conflicts = 0
    _count_lock = threading.Lock()

    def commit(self, commit: Commit, **kwargs: Any):
        try:
            return super().commit(commit, **kwargs)  # type: ignore[misc]
        except RevisionConflict:
            with self._count_lock:
                self.conflicts += 1
            raise


class CountingMemory(Counting, MemoryStore):
    pass


def chain_of(i: int) -> int:
    return (i - 1) // CHAIN


def plan_for(n: int, extra_field: bool = False) -> tuple[list[Task], list[Contract], list]:
    """Chains of CHAIN tasks; task i provides c<i> to task i+1 within its chain."""
    tasks, contracts = [], []
    requirements = [
        Requirement(id=f"R-{c + 1}", description=f"Pipeline {c + 1} works end to end")
        for c in range(chain_of(n) + 1)
    ]
    for i in range(1, n + 1):
        nxt = i + 1 if i < n and chain_of(i + 1) == chain_of(i) else None
        prev = i - 1 if i > 1 and chain_of(i - 1) == chain_of(i) else None
        tasks.append(
            Task(
                id=f"T{i}",
                title=f"Stage {i}",
                owner=f"p-{i}",
                branch=f"t{i}",
                requirement_ids=[f"R-{chain_of(i) + 1}"],
                provides=[f"c{i}"] if nxt else [],
                consumes=[f"c{prev}"] if prev else [],
            )
        )
        if nxt:
            fields = {"amount": FieldType.INTEGER}
            if extra_field and i == 1:
                fields["currency"] = FieldType.STRING
            contracts.append(
                Contract(
                    id=f"c{i}",
                    version=1,
                    provider_task=f"T{i}",
                    consumer_tasks=[f"T{nxt}"],
                    fields=fields,
                )
            )
    return tasks, contracts, requirements


def seed(store: Store, n: int, now) -> None:
    tasks, contracts, requirements = plan_for(n)
    people = [
        Participant(
            id=LEAD, project_id=PROJECT, role=Role.LEAD, developer_name="lead", user_id="u-lead"
        ),
        *(
            Participant(
                id=f"p-{i}",
                project_id=PROJECT,
                role=Role.AGENT,
                developer_name=f"dev{i}",
                user_id=f"u-{i}",
            )
            for i in range(1, n + 1)
        ),
    ]
    project = Project(
        id=PROJECT,
        repository="bench/shop",
        lead_id=LEAD,
        participant_ids=[p.id for p in people],
        current_plan_version=1,
    )
    plan = Plan(
        project_id=PROJECT,
        version=1,
        status=PlanStatus.APPROVED,
        requirements=requirements,
        tasks=tasks,
        contracts=contracts,
        approved_by=LEAD,
        approved_at=now,
        change_reason="starting plan",
    )
    store.commit(Commit(PROJECT, "seed", puts=[project, *people, plan]))


def drifts(i: int, n: int) -> bool:
    """The second task of every other chain reads the wrong field name."""
    return (i - 1) % CHAIN == 1 and chain_of(i) % 2 == 0 and i <= n


def submission(task: Task, drift: bool) -> ClaimSubmission:
    def use(contract: str, consumer: bool) -> InterfaceUse:
        name = "total" if consumer and drift else "amount"
        return InterfaceUse(contract_id=contract, fields={name: FieldType.INTEGER})

    return ClaimSubmission(
        task_id=task.id,
        branch=task.branch or task.id.lower(),
        base_sha="abc1234",
        plan_version=1,
        requirement_ids=task.requirement_ids,
        files=[f"app/{task.id.lower()}.py"],
        provides=[use(c, False) for c in task.provides],
        consumes=[use(c, True) for c in task.consumes],
        no_interfaces=not (task.provides or task.consumes),
        assumptions=[f"{task.id} uses integer cents for amount"],
        acceptance_criteria=[f"{task.id} passes its contract tests"],
    )


def percentile(values: list[float], p: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, round(p * (len(ordered) - 1)))]


class ConcurrentRunner:
    """Runs each job in its caller's thread with no lock: reviews side by side, as worker
    Lambdas reading different stream shards would."""

    def __init__(self) -> None:
        self._handlers: dict[JobKind, Callable[[Any], None]] = {}

    def register(self, kind: JobKind, handler: Callable[[Any], None]) -> None:
        self._handlers[kind] = handler

    def submit(self, job: Any) -> None:
        self._handlers[job.kind](job)


class SlowReviewer:
    """Stands in for the AI reviewer: takes as long as a model call and finds nothing."""

    def __init__(self, seconds: float) -> None:
        self.seconds = seconds

    def review_claim(self, request: object) -> list:
        time.sleep(self.seconds)
        return []

    def review_commit(self, request: object) -> list:
        return []


def run_once(
    make_store: Callable[[], tuple[Any, Callable[[], None]]],
    n: int,
    runner_kind: str,
    review_s: float = 0,
    spread_s: float = 0,
    seed_value: int = 0,
) -> dict:
    """`runner_kind` is "inline" (the local server's InlineRunner), "concurrent" (reviews
    side by side) or "worker" (RecoverableWorker). `review_s` > 0 adds a reviewer that
    takes that long; `spread_s` > 0 has agents submit at random moments over that many
    seconds instead of all at once."""
    raw, cleanup = make_store()
    rng = random.Random(seed_value)
    runner = None
    try:
        clock = SystemClock()
        seed(raw, n, clock.now())
        if runner_kind == "worker":
            # As the Graph Hacks server runs it: one worker thread, the database as queue.
            runner = RecoverableWorker(raw, clock, poll_interval=0.05, retry_delay=0.05)
        elif runner_kind == "concurrent":
            runner = ConcurrentRunner()
        reviewer = SlowReviewer(review_s) if review_s else None
        services = build_services(raw, clock, reviewer, runner=runner)
        if runner is not None:
            runner.register(JobKind.CLAIM_REVIEW, services.claims.run_review)
        if isinstance(runner, RecoverableWorker):
            runner.start()
        tasks, _, _ = plan_for(n)

        # 1 and 2: every agent claims at the same instant, or spread over spread_s.
        barrier = threading.Barrier(n)
        delays = {t.id: rng.uniform(0, spread_s) for t in tasks}
        latencies: dict[str, float] = {}
        errors: list[str] = []

        def agent(task: Task) -> None:
            actor = raw.get_participant(task.owner)
            body = submission(task, drifts(int(task.id[1:]), n))
            barrier.wait()
            time.sleep(delays[task.id])
            start = time.perf_counter()
            try:
                services.claims.submit(actor, body)
            except Exception as error:  # recorded, never hidden
                errors.append(f"{task.id}: {type(error).__name__}: {error}")
            latencies[task.id] = time.perf_counter() - start

        threads = [threading.Thread(target=agent, args=(t,)) for t in tasks]
        wall = time.perf_counter()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        while isinstance(runner, RecoverableWorker) and any(
            j.state not in (JobState.SUCCEEDED, JobState.FAILED) for j in raw.list_jobs(PROJECT)
        ):
            time.sleep(0.02)
        wall = time.perf_counter() - wall

        claims = {c.task_id: c for c in raw.list_claims(PROJECT)}
        jobs = raw.list_jobs(PROJECT)
        planted = {t.id for t in tasks if drifts(int(t.id[1:]), n)}
        stopped = {tid for tid, c in claims.items() if c.state in STOPPED}
        approved = {tid for tid, c in claims.items() if c.state is ClaimState.APPROVED}
        gave_up = sum(j.state is JobState.FAILED for j in jobs)
        claim_conflicts = raw.conflicts

        # 3: every agent checks in once.
        sizes, check_ms = [], []
        for task in tasks:
            start = time.perf_counter()
            reply = services.check_ins.check_in(raw.get_participant(task.owner), task_id=task.id)
            check_ms.append((time.perf_counter() - start) * 1000)
            sizes.append(len(check_in_text(check_in_json(reply))))

        # 4: the lead adds a field to c1.
        lead = raw.get_participant(LEAD)
        new_tasks, new_contracts, requirements = plan_for(n, extra_field=True)
        start = time.perf_counter()
        draft = services.plans.propose(
            lead, PlanDraft(requirements=requirements, tasks=new_tasks, contracts=new_contracts)
        )
        services.plans.approve(lead, draft.version, "c1 gains currency")
        approve_ms = (time.perf_counter() - start) * 1000
        directed = sorted(
            {d.task_id for d in raw.list_directives(PROJECT) if d.plan_version == draft.version},
            key=lambda t: int(t[1:]),
        )
        return {
            "agents": n,
            "claim_wall_s": wall,
            "claim_p50_ms": percentile(list(latencies.values()), 0.5) * 1000,
            "claim_p95_ms": percentile(list(latencies.values()), 0.95) * 1000,
            "approved": len(approved),
            "stopped": len(stopped),
            "pending_or_draft": n - len(approved) - len(stopped),
            "reviews_gave_up": gave_up,
            "revision_conflicts": claim_conflicts,
            "planted": len(planted),
            "caught": len(planted & stopped),
            "false_alarms": len(stopped - planted),
            "errors": errors,
            "checkin_chars_mean": statistics.mean(sizes),
            "checkin_chars_max": max(sizes),
            "checkin_ms_mean": statistics.mean(check_ms),
            "approve_ms": approve_ms,
            "directed": directed,
        }
    finally:
        if isinstance(runner, RecoverableWorker):
            runner.stop()
        cleanup()


def memory() -> tuple[Any, Callable[[], None]]:
    return CountingMemory(), lambda: None


def falkordb() -> tuple[Any, Callable[[], None]]:
    from midflight.adapters.falkor_store import FalkorStore

    class CountingFalkor(Counting, FalkorStore):
        pass

    store = CountingFalkor.connect(graph_name="bench_" + uuid.uuid4().hex, port=6379)

    def cleanup() -> None:
        store.graph.delete()
        store.close()

    return store, cleanup


def summarize(runs: list[dict]) -> dict:
    first = runs[0]
    out: dict[str, Any] = {"agents": first["agents"], "repeats": len(runs)}
    for key in first:
        if key in ("agents", "errors", "directed"):
            continue
        out[key] = statistics.median(r[key] for r in runs)
        if key in ("reviews_gave_up", "revision_conflicts", "pending_or_draft", "false_alarms"):
            out[key + "_max"] = max(r[key] for r in runs)
    out["directed"] = first["directed"]
    out["directed_same_every_run"] = all(r["directed"] == first["directed"] for r in runs)
    out["errors"] = sorted({e for r in runs for e in r["errors"]})
    return out


def table(backend: str, rows: list[dict]) -> str:
    head = [
        "Agents", "Claims wall (s)", "p50 / p95 per claim (ms)", "Approved", "Stopped",
        "Gave up (max)", "Conflicts", "Drift caught", "False alarms", "Check-in chars",
        "Approve change (ms)", "Got a directive",
    ]  # fmt: skip
    lines = [f"### {backend}", "", "| " + " | ".join(head) + " |", "|" + " --- |" * len(head)]
    for r in rows:
        directed = r["directed"]
        shown = ", ".join(directed) if len(directed) <= 4 else f"{len(directed)} tasks"
        lines.append(
            "| "
            + " | ".join(
                [
                    str(r["agents"]),
                    f"{r['claim_wall_s']:.2f}",
                    f"{r['claim_p50_ms']:.0f} / {r['claim_p95_ms']:.0f}",
                    f"{r['approved']:.0f}",
                    f"{r['stopped']:.0f}",
                    f"{r['reviews_gave_up']:.0f} ({r['reviews_gave_up_max']})",
                    f"{r['revision_conflicts']:.0f}",
                    f"{r['caught']:.0f} of {r['planted']:.0f}",
                    f"{r['false_alarms']:.0f}",
                    f"{r['checkin_chars_mean']:.0f}",
                    f"{r['approve_ms']:.0f}",
                    shown,
                ]
            )
            + " |"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--falkordb", action="store_true", help="also run against FalkorDB")
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--sizes", type=int, nargs="*", default=SIZES)
    parser.add_argument("--json", type=Path, help="write every run's numbers here")
    parser.add_argument("--review", type=float, default=0.5, help="slow reviewer seconds")
    parser.add_argument("--spread", type=float, default=5.0, help="claims arrive over (s)")
    parser.add_argument("--slow-max", type=int, default=32, help="largest team, slow runs")
    args = parser.parse_args()

    # (name, store, runner, reviewer seconds, submit spread seconds, sizes)
    slow = [n for n in args.sizes if n <= args.slow_max]
    later = f"{args.review}s reviewer, claims over {args.spread}s"
    configs = [
        ("memory, reviews inline (local server)", memory, "inline", 0, 0, args.sizes),
        (f"memory, reviews inline, {later}", memory, "inline", args.review, args.spread, slow),
    ]
    if args.falkordb:
        configs += [
            ("FalkorDB, one worker (Graph Hacks server)", falkordb, "worker", 0, 0, args.sizes),
            (
                "FalkorDB, concurrent reviews (like many Lambda workers)",
                falkordb, "concurrent", 0, 0, args.sizes,
            ),
            (f"FalkorDB, one worker, {later}", falkordb, "worker", args.review, args.spread, slow),
            (
                f"FalkorDB, concurrent reviews, {later}",
                falkordb, "concurrent", args.review, args.spread, slow,
            ),
        ]  # fmt: skip
    results: dict[str, list[dict]] = {}
    for name, make, runner_kind, review_s, spread_s, sizes in configs:
        rows = []
        for n in sizes:
            runs = [
                run_once(make, n, runner_kind, review_s, spread_s, seed_value=n * 100 + rep)
                for rep in range(args.repeat)
            ]
            row = summarize(runs)
            rows.append(row)
            print(
                f"{name[:24]:24} n={n:3} approved={row['approved']:.0f} "
                f"stopped={row['stopped']:.0f} "
                f"gave_up={row['reviews_gave_up']:.0f} conflicts={row['revision_conflicts']:.0f} "
                f"wall={row['claim_wall_s']:.2f}s directed={row['directed']}",
                flush=True,
            )
        results[name] = rows
        print()
        print(table(name, rows))
        print()
    if args.json:
        args.json.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
