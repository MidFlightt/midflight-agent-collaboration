"""Generate local confirmation messages; do not send email."""

import re


_LOCAL_PART = re.compile(r"[A-Za-z0-9!#$%&'*+/=?^_`{|}~.-]+")
_DOMAIN_LABEL = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?")


def confirmation(email: str, delivery_id: int) -> str:
    """Return a local message for a positive delivery ID and ASCII email address.

    Validate syntax only: this does not verify a mailbox or delivery exists.
    """
    if not isinstance(email, str) or len(email) > 254 or email.count("@") != 1:
        raise ValueError("email must be a valid email address")
    local, domain = email.split("@")
    labels = domain.split(".")
    if (
        not 1 <= len(local) <= 64
        or not _LOCAL_PART.fullmatch(local)
        or local.startswith(".")
        or local.endswith(".")
        or ".." in local
        or len(labels) < 2
        or any(not _DOMAIN_LABEL.fullmatch(label) for label in labels)
    ):
        raise ValueError("email must be a valid email address")
    if isinstance(delivery_id, bool) or not isinstance(delivery_id, int) or delivery_id <= 0:
        raise ValueError("delivery_id must be a positive integer")
    return f"Delivery {delivery_id} is confirmed. Confirmation for {email}."
