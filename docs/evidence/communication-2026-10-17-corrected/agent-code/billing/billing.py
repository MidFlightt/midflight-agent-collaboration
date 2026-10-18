"""Revenue reporting from saved delivery totals and refunds."""
from delivery import get_delivery_records


def summarize_records(records: list[dict]) -> dict:
    """Summarize a flat list of saved delivery dictionaries.

    Records contain integer total_cents/refund_cents and a confirmed or cancelled
    status. Extra delivery fields are allowed. Revenue uses the actual saved
    amounts, including partial refunds, rather than inferring refunds from status.
    """
    if not isinstance(records, list):
        raise TypeError("records must be a list of delivery dictionaries")

    report = {"revenue_cents": 0, "confirmed": 0, "cancelled": 0}
    for record in records:
        if not isinstance(record, dict):
            raise TypeError("each delivery record must be a dictionary")
        total = record["total_cents"]
        refund = record["refund_cents"]
        status = record["status"]
        for field, amount in (("total_cents", total), ("refund_cents", refund)):
            if type(amount) is not int:
                raise TypeError(f"{field} must be integer cents")
            if amount < 0:
                raise ValueError(f"{field} must be nonnegative")
        if refund > total:
            raise ValueError("refund_cents must not exceed total_cents")
        if status not in ("confirmed", "cancelled"):
            raise ValueError("status must be confirmed or cancelled")
        report["revenue_cents"] += total - refund
        report[status] += 1
    return report


def revenue_report() -> dict:
    """Report revenue from get_delivery_records(): flat list[dict], [] if empty."""
    return summarize_records(get_delivery_records())
