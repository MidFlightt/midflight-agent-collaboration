"""Report revenue from saved delivery amounts."""
from delivery import get_delivery_records


def summarize_records(records: dict[int, dict] | list[dict]) -> dict:
    """Return revenue_cents and confirmed/cancelled counts without mutation.

    Accept the delivery-record boundary's ID-keyed dictionary ({} when empty),
    or a flat list for existing callers. Amounts are nonnegative integer cents;
    booleans and unknown statuses are invalid. Saved amounts follow current
    policy; billing always subtracts the actual saved refund.
    """
    if not isinstance(records, (dict, list)):
        raise ValueError("records must be an ID-keyed dictionary or a list")
    entries = records.items() if isinstance(records, dict) else ((None, r) for r in records)
    report = {"revenue_cents": 0, "confirmed": 0, "cancelled": 0}
    for record_id, record in entries:
        if not isinstance(record, dict):
            raise ValueError("each record must be a dictionary")
        if isinstance(records, dict):
            if (type(record_id) is not int or record_id <= 0
                    or type(record.get("id")) is not int
                    or record["id"] != record_id):
                raise ValueError("record keys must be positive IDs matching record id")
        for field in ("total_cents", "refund_cents"):
            amount = record.get(field)
            if type(amount) is not int or amount < 0:
                raise ValueError(f"{field} must be nonnegative integer cents")
        status = record.get("status")
        if status not in ("confirmed", "cancelled"):
            raise ValueError("status must be confirmed or cancelled")
        report["revenue_cents"] += record["total_cents"] - record["refund_cents"]
        report[status] += 1
    return report


def revenue_report() -> dict:
    """Read delivery.get_delivery_records(): dict[int, dict], {} when empty.

    Each key matches its record's positive integer id. Records contain status,
    total_cents and refund_cents as defined by the delivery-record interface.
    """
    return summarize_records(get_delivery_records())
