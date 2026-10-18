"""Revenue reports from saved delivery totals and refunds."""
from delivery import get_delivery_records


def summarize_records(records: list[dict] | dict[int, dict]) -> dict:
    """Summarize an ID-keyed delivery snapshot or a legacy flat list.

    Each record supplies nonnegative integer total_cents and refund_cents,
    and status ('confirmed' or 'cancelled'). Saved refunds determine revenue
    independently of status. Input records are never modified.
    """
    if isinstance(records, dict):
        rows = records.values()
    elif isinstance(records, list):
        rows = records
    else:
        raise TypeError("records must be an ID-keyed dictionary or a list")

    report = {"revenue_cents": 0, "confirmed": 0, "cancelled": 0}
    for record in rows:
        if not isinstance(record, dict):
            raise TypeError("each record must be a dictionary")
        for field in ("total_cents", "refund_cents"):
            value = record[field]
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{field} must be an integer")
            if value < 0:
                raise ValueError(f"{field} must be nonnegative")
        status = record["status"]
        if status not in ("confirmed", "cancelled"):
            raise ValueError("status must be confirmed or cancelled")
        report["revenue_cents"] += record["total_cents"] - record["refund_cents"]
        report[status] += 1
    return report


def revenue_report() -> dict:
    """Read delivery's public dict[int, dict] snapshot and summarize it.

    Return revenue_cents, confirmed count, and cancelled count, all integers;
    an empty snapshot returns zeros. Legacy list snapshots are also supported.
    """
    return summarize_records(get_delivery_records())
