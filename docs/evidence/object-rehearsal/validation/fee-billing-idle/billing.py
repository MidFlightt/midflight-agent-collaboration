"""Revenue reporting from saved delivery amounts."""
from delivery import get_delivery_records


def summarize_records(records: list[dict]) -> dict:
    """Summarize saved records without changing or recalculating their refunds.

    Amounts are nonnegative integer cents (excluding bool) saved under current
    policy. Status must be confirmed or cancelled. Invalid records raise ValueError.
    """
    result = {"revenue_cents": 0, "confirmed": 0, "cancelled": 0}
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("delivery record must be a dictionary")
        for field in ("total_cents", "refund_cents"):
            value = record.get(field)
            if type(value) is not int or value < 0:
                raise ValueError(f"{field} must be nonnegative integer cents")
        status = record.get("status")
        if status not in ("confirmed", "cancelled"):
            raise ValueError("status must be confirmed or cancelled")
        result["revenue_cents"] += record["total_cents"] - record["refund_cents"]
        result[status] += 1
    return result


def revenue_report() -> dict:
    """Read get_delivery_records() -> dict[int, dict], with {} when empty.

    Delivery's published boundary provides copied saved records keyed by ID.
    """
    return summarize_records(list(get_delivery_records().values()))
