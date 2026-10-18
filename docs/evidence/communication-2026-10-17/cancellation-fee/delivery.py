"""In-memory delivery management with copied public snapshots."""
_records = {}
_next_id = 1


def _integer(value: int, name: str, minimum: int) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{name} must be an integer")
    if value < minimum:
        raise ValueError(f"{name} must be at least {minimum}")


def get_delivery_records() -> dict[int, dict]:
    """Return ID-keyed record copies; iteration yields IDs, not records."""
    return {key: record.copy() for key, record in _records.items()}


def create_delivery(total_cents: int, customer: str, destination: str) -> dict:
    global _next_id
    _integer(total_cents, "total_cents", 0)
    for name, value in (("customer", customer), ("destination", destination)):
        if not isinstance(value, str):
            raise TypeError(f"{name} must be a string")
        if not value.strip():
            raise ValueError(f"{name} must not be blank")
    record = {"delivery_id": _next_id, "total_cents": total_cents,
              "customer": customer, "destination": destination,
              "status": "confirmed", "refund_cents": 0}
    _records[_next_id] = record
    _next_id += 1
    return record.copy()


def get_delivery(delivery_id: int) -> dict:
    _integer(delivery_id, "delivery_id", 1)
    return _records[delivery_id].copy()


def cancel_delivery(delivery_id: int) -> dict:
    _integer(delivery_id, "delivery_id", 1)
    record = _records[delivery_id]
    if record["status"] != "cancelled":
        record["refund_cents"] = max(record["total_cents"] - 400, 0)
        record["status"] = "cancelled"
    return record.copy()
