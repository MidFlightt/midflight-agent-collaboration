"""Generate local confirmation messages; do not send email."""


def confirmation(email: str, delivery_id: int) -> str:
    """Return a local confirmation after basic address and identifier validation.

    Addresses require one @ and a dotted domain with nonempty labels. Inputs
    are preserved, never stripped or coerced. No delivery lookup is performed.
    """
    if not isinstance(email, str) or any(char.isspace() for char in email):
        raise ValueError("email must be an address with a dotted domain")
    if email.count("@") != 1:
        raise ValueError("email must be an address with a dotted domain")
    local, domain = email.split("@")
    if not local or "." not in domain or not all(domain.split(".")):
        raise ValueError("email must be an address with a dotted domain")
    if isinstance(delivery_id, bool) or not isinstance(delivery_id, int) or delivery_id <= 0:
        raise ValueError("delivery_id must be a positive integer")
    return f"Delivery {delivery_id} confirmed for {email}."
