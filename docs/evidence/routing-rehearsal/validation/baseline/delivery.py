"""In-memory delivery management with independent record snapshots."""
_records = {}


def get_delivery_records() -> dict[int, dict]:
    """Return records keyed by ID, copying both the mapping and each record."""
    return {key: record.copy() for key, record in _records.items()}


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a nonempty string")
    return value.strip()


def _record(delivery_id):
    if type(delivery_id) is not int or delivery_id <= 0:
        raise ValueError("delivery_id must be a positive integer")
    if delivery_id not in _records:
        raise ValueError("Unknown delivery ID")
    return _records[delivery_id]


def create_delivery(total_cents: int, customer: str, destination: str) -> dict:
    if type(total_cents) is not int or total_cents < 0:
        raise ValueError("total_cents must be a nonnegative integer")
    customer = _text(customer, "customer")
    destination = _text(destination, "destination")
    delivery_id = max(_records, default=0) + 1
    record = dict(id=delivery_id, total_cents=total_cents, customer=customer,
                  destination=destination, status="confirmed", refund_cents=0)
    _records[delivery_id] = record
    return record.copy()


def get_delivery(delivery_id: int) -> dict:
    return _record(delivery_id).copy()


def cancel_delivery(delivery_id: int) -> dict:
    record = _record(delivery_id)
    if record["status"] == "confirmed":
        record["refund_cents"] = record["total_cents"]
        record["status"] = "cancelled"
    return record.copy()
