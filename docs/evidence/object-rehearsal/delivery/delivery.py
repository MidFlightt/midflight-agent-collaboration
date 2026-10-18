"""In-memory delivery management with copied public snapshots."""
_records = {}


def get_delivery_records() -> dict[int, dict]:
    """Return ID-keyed copies of records, including saved refund_cents."""
    return {key: record.copy() for key, record in _records.items()}


def create_delivery(total_cents: int, customer: str, destination: str) -> dict:
    if type(total_cents) is not int or total_cents < 0:
        raise ValueError("total_cents must be a nonnegative integer")
    for name, value in (("customer", customer), ("destination", destination)):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} must be a nonblank string")
    delivery_id = max(_records, default=0) + 1
    record = {
        "id": delivery_id,
        "total_cents": total_cents,
        "customer": customer.strip(),
        "destination": destination.strip(),
        "status": "confirmed",
        "refund_cents": 0,
    }
    _records[delivery_id] = record
    return record.copy()


def _record(delivery_id: int) -> dict:
    if type(delivery_id) is not int or delivery_id <= 0:
        raise ValueError("delivery_id must be a positive integer")
    return _records[delivery_id]


def get_delivery(delivery_id: int) -> dict:
    return _record(delivery_id).copy()


def cancel_delivery(delivery_id: int) -> dict:
    record = _record(delivery_id)
    if record["status"] != "cancelled":
        record["status"] = "cancelled"
        record["refund_cents"] = max(record["total_cents"] - 400, 0)
    return record.copy()
