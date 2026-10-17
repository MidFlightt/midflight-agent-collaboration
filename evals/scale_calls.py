"""Count the reviewer's model calls in the scale benchmark's local-server setup.

Runs the "memory, reviews inline, 0.5 s reviewer, claims over 5 s" setup of
scale_benchmark.py at 8, 16, and 32 agents, 3 times each, and prints how many times the
stand-in reviewer was asked, with approvals, give-ups, and the median and 95th percentile
wait per claim in ms. Used for the model-call table in scale-results.md.

    uv run python evals/scale_calls.py
"""

from __future__ import annotations

import statistics
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import scale_benchmark as bench  # noqa: E402

calls = {"n": 0}
lock = threading.Lock()
asked = bench.SlowReviewer.review_claim


def counted(self: bench.SlowReviewer, request: object) -> list:
    with lock:
        calls["n"] += 1
    return asked(self, request)


bench.SlowReviewer.review_claim = counted  # type: ignore[method-assign]

for n in (8, 16, 32):
    runs = []
    for rep in range(3):
        calls["n"] = 0
        r = bench.run_once(bench.memory, n, "inline", 0.5, 5.0, seed_value=n * 100 + rep)
        runs.append((calls["n"], r["approved"], r["reviews_gave_up"],
                     round(r["claim_p50_ms"]), round(r["claim_p95_ms"])))  # fmt: skip
    print(n, "reviewer calls (median):", statistics.median(c for c, *_ in runs), runs)
