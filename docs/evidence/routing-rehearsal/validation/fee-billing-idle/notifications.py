"""Generate local confirmation messages; do not send email."""

import re


_LOCAL_PART = re.compile(r"[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+)*", re.ASCII)
_DOMAIN_LABEL = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?", re.ASCII)


def confirmation(email: str, delivery_id: int) -> str:
    """Validate a recipient and positive ID, then return a local confirmation.

    Addresses use an ASCII dot-atom local part and dotted DNS domain. Quoted
    local parts, address literals, display names and surrounding spaces are
    intentionally unsupported. No delivery lookup or outbound email is performed.
    """
    if not isinstance(email, str):
        raise TypeError("email must be a string")
    if len(email) > 254 or email.count("@") != 1:
        raise ValueError("email must be a valid email address")
    local, domain = email.split("@")
    labels = domain.split(".")
    if (len(local) > 64 or _LOCAL_PART.fullmatch(local) is None
            or len(labels) < 2
            or any(_DOMAIN_LABEL.fullmatch(label) is None for label in labels)):
        raise ValueError("email must be a valid email address")
    if not isinstance(delivery_id, int) or isinstance(delivery_id, bool):
        raise TypeError("delivery_id must be an integer")
    if delivery_id <= 0:
        raise ValueError("delivery_id must be positive")
    return f"Delivery {delivery_id} confirmed for {email}."
