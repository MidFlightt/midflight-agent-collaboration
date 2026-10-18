"""Evidence summaries: missing metrics remain null, never fabricated zeroes."""

import json
from pathlib import Path

FIELDS = (
    "input_tokens",
    "cached_input_tokens",
    "output_tokens",
    "cache_write_input_tokens",
    "reasoning_output_tokens",
)


def summarize(root):
    root = Path(root)
    rows = [json.loads(p.read_text()) for p in sorted((root / "logs").glob("*.result.json"))]
    previous = {}
    normalized = []
    for row in rows:
        raw = row.get("usage")
        session = row.get("session_id")
        prior = previous.get(session, {})
        delta = (
            None
            if raw is None
            else {
                field: raw[field] - prior.get(field, 0)
                if raw.get(field) is not None
                and prior.get(field, 0) is not None
                and raw[field] >= prior.get(field, 0)
                else None
                for field in FIELDS
            }
        )
        if raw is not None:
            previous[session] = raw
        normalized.append({**row, "raw_cumulative_usage": raw, "usage": delta})
    rows = normalized
    totals = {}
    for category in ("building", "lead", "repair", "overhead", "all_in"):
        selected = rows if category == "all_in" else [r for r in rows if r["category"] == category]
        totals[category] = {"calls": len(selected), "actual_cost_usd": None, "usage": {}}
        for field in FIELDS:
            values = [(r.get("usage") or {}).get(field) for r in selected]
            totals[category]["usage"][field] = (
                sum(values) if all(v is not None for v in values) else None
            )
    state = json.loads((root / "state.json").read_text())
    scores = state.get("scores", [])
    checks = scores[0]["checks"] if scores else None
    traces = []
    for path in sorted((root / "profiles").glob("*/bridge.jsonl")):
        for line in path.read_text().splitlines():
            traces.append({"agent": path.parent.name, **json.loads(line)})
    report = {
        "usage": totals,
        "first_merge": None
        if checks is None
        else {"passed": sum(c["passed"] for c in checks), "of": len(checks), "checks": checks},
        "score_rounds": scores,
        "first_merge_events": scores[0].get("events") if scores else None,
        "usage_accounting": "successive cumulative session snapshots differenced by session_id",
        "call_usage": [
            {k: r.get(k) for k in ("agent", "category", "usage", "raw_cumulative_usage")}
            for r in rows
        ],
        "repair_rounds": sum(r["category"] == "repair" for r in rows),
        "validation_runner": "benchmark operator harness: unchanged PigeonPost score.py",
        "call_statuses": [{k: r[k] for k in ("agent", "status", "returncode")} for r in rows],
        "communication_trace_calls": len(traces),
        "evidence_rules": {
            "routed": "server recipient list",
            "delivered": "inbox in client result; bridge response alone is transport evidence",
            "observably_read": "explicit exact-update reference; operator audits transcript",
            "applied": "agent report referencing exact update; separately compare owned code diff",
            "tests": "operator-run combined code, not proof of message consumption",
        },
        "semantic_audit_status": "pending operator transcript audit"
        if traces
        else "not applicable",
    }
    (root / "pilot-summary.json").write_text(json.dumps(report, indent=2))
    # Private evidence only; these records can contain source messages and session IDs.
    (root / "communication-traces.json").write_text(json.dumps(traces, indent=2))
    return report
