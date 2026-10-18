"""In-memory delivery management with isolated public snapshots."""
_records = {}
CANCELLATION_FEE_CENTS = 400


def _integer(value, name, minimum):
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return value


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a nonblank string")
    return value.strip()


def get_delivery_records() -> list[dict]:
    """Return a flat list of copied records, or [] when empty.

    Records contain delivery_id, total_cents, customer, destination, status,
    and refund_cents. Mutating the list or its records cannot alter the store.
    """
    return [record.copy() for record in _records.values()]


def create_delivery(total_cents: int, customer: str, destination: str) -> dict:
    """Validate and save a confirmed delivery, returning a copied record."""
    total_cents = _integer(total_cents, "total_cents", 0)
    customer = _text(customer, "customer")
    destination = _text(destination, "destination")
    delivery_id = max(_records, default=0) + 1
    record = dict(delivery_id=delivery_id, total_cents=total_cents,
                  customer=customer, destination=destination,
                  status="confirmed", refund_cents=0)
    _records[delivery_id] = record
    return record.copy()


def get_delivery(delivery_id: int) -> dict:
    """Return a copied record; raise KeyError for an unknown valid ID."""
    return _records[_integer(delivery_id, "delivery_id", 1)].copy()


def cancel_delivery(delivery_id: int) -> dict:
    """Save the refund after a four-credit fee, with a zero minimum."""
    record = _records[_integer(delivery_id, "delivery_id", 1)]
    if record["status"] != "cancelled":
        record["status"] = "cancelled"
        record["refund_cents"] = max(record["total_cents"] - CANCELLATION_FEE_CENTS, 0)
    return record.copy()
