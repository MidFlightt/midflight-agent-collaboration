"""Generate local confirmation messages; do not send email."""

import re


_EMAIL = re.compile(
    r"[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+"
    r"(?:\.[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+)*@"
    r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)+"
)


def confirmation(email: str, delivery_id: int) -> str:
    """Return a local message for a plain email address and positive delivery ID.

    Invalid inputs raise ValueError. This formats supplied details without
    looking up a delivery or contacting a mail service.
    """
    if not isinstance(email, str) or _EMAIL.fullmatch(email) is None:
        raise ValueError("email must be a valid plain email address")
    if isinstance(delivery_id, bool) or not isinstance(delivery_id, int) or delivery_id <= 0:
        raise ValueError("delivery_id must be a positive integer")
    return f"Delivery {delivery_id} confirmed for {email}."
