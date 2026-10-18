"""In-memory deliveries with copied public records and saved refunds."""
_records = {}
_next_id = 1


def _integer(value, name, minimum):
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if value < minimum:
        raise ValueError(f"{name} must be at least {minimum}")


def _text(value, name):
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    if not value.strip():
        raise ValueError(f"{name} must not be blank")


def get_delivery_records() -> dict[int, dict]:
    """Return an ID-keyed snapshot; neither dict level aliases stored records."""
    return {key: record.copy() for key, record in _records.items()}


def create_delivery(total_cents: int, customer: str, destination: str) -> dict:
    global _next_id
    _integer(total_cents, "total_cents", 0)
    _text(customer, "customer")
    _text(destination, "destination")
    record = {"id": _next_id, "total_cents": total_cents,
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
        record["refund_cents"] = record["total_cents"]
        record["status"] = "cancelled"
    return record.copy()
