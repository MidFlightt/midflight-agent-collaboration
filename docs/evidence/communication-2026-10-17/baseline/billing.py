"""Revenue reporting from saved delivery totals and refunds."""
from delivery import get_delivery_records


def summarize_records(records: list[dict]) -> dict:
    """Sum saved total_cents minus refund_cents and count delivery statuses."""
    return {"revenue_cents": sum(r["total_cents"] - r["refund_cents"] for r in records),
            "confirmed": sum(r["status"] == "confirmed" for r in records),
            "cancelled": sum(r["status"] == "cancelled" for r in records)}


def revenue_report() -> dict:
    """Report on get_delivery_records(): dict[int, dict], or {} when empty.

    Each record supplies integer total_cents and refund_cents and a status.
    Refund amounts come from the saved records, regardless of current policy.
    """
    return summarize_records(list(get_delivery_records().values()))
