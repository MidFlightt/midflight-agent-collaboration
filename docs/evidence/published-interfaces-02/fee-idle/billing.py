"""Revenue reports calculated from saved delivery amounts."""
from delivery import get_delivery_records


def _amount(record: dict, field: str) -> int:
    value = record[field]
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field} must be an integer")
    if value < 0:
        raise ValueError(f"{field} must be nonnegative")
    return value


def summarize_records(records: dict[int, dict] | list[dict]) -> dict:
    """Summarize an ID-keyed delivery snapshot (or a legacy flat list).

    Records must contain nonnegative integer total_cents and refund_cents and
    status 'confirmed' or 'cancelled'. Missing fields raise KeyError, invalid
    types raise TypeError, and invalid values raise ValueError. Saved amounts
    follow current policy; reporting uses them without recalculating refunds.
    """
    if isinstance(records, dict):
        for delivery_id in records:
            if isinstance(delivery_id, bool) or not isinstance(delivery_id, int):
                raise TypeError("delivery IDs must be integers")
            if delivery_id <= 0:
                raise ValueError("delivery IDs must be positive")
        values = records.values()
    elif isinstance(records, list):
        values = records
    else:
        raise TypeError("records must be an ID-keyed dictionary or a list")

    report = {"revenue_cents": 0, "confirmed": 0, "cancelled": 0}
    for record in values:
        if not isinstance(record, dict):
            raise TypeError("each record must be a dictionary")
        total = _amount(record, "total_cents")
        refund = _amount(record, "refund_cents")
        status = record["status"]
        if not isinstance(status, str):
            raise TypeError("status must be a string")
        if status not in ("confirmed", "cancelled"):
            raise ValueError("status must be confirmed or cancelled")
        report["revenue_cents"] += total - refund
        report[status] += 1
    return report


def revenue_report() -> dict:
    """Return revenue_cents, confirmed, and cancelled as integer totals.

    get_delivery_records() supplies dict[int, dict], keyed by positive delivery
    ID, with {} for no deliveries, as published by the delivery owner.
    """
    return summarize_records(get_delivery_records())
