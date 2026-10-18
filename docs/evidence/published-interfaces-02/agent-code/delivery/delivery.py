"""In-memory delivery management with copied public snapshots."""
_records = {}


def get_delivery_records() -> dict[int, dict]:
    """Return ID-keyed snapshots; iteration yields IDs, not records."""
    return {key: record.copy() for key, record in _records.items()}


def create_delivery(total_cents: int, customer: str, destination: str) -> dict:
    _integer(total_cents, "total_cents", minimum=0)
    for name, value in (("customer", customer), ("destination", destination)):
        if not isinstance(value, str):
            raise TypeError(f"{name} must be a string")
        if not value.strip():
            raise ValueError(f"{name} must not be blank")
    delivery_id = max(_records, default=0) + 1
    record = {"id": delivery_id, "total_cents": total_cents,
              "customer": customer, "destination": destination,
              "status": "confirmed", "refund_cents": 0}
    _records[delivery_id] = record
    return record.copy()


def get_delivery(delivery_id: int) -> dict:
    _integer(delivery_id, "delivery_id", minimum=1)
    return _records[delivery_id].copy()


def cancel_delivery(delivery_id: int) -> dict:
    _integer(delivery_id, "delivery_id", minimum=1)
    record = _records[delivery_id]
    if record["status"] != "cancelled":
        record["refund_cents"] = max(record["total_cents"] - 400, 0)
        record["status"] = "cancelled"
    return record.copy()


def _integer(value: int, name: str, minimum: int) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{name} must be an integer")
    if value < minimum:
        raise ValueError(f"{name} must be at least {minimum}")
