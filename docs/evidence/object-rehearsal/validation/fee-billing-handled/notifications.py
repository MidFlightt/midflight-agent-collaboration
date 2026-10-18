"""Generate local confirmation messages; do not send email."""


def confirmation(email: str, delivery_id: int) -> str:
    """Return a local confirmation for a valid email and positive delivery ID.

    This demo accepts a simple address form, not every RFC mailbox syntax.
    It does not verify mailbox ownership or delivery existence.
    """
    if not isinstance(email, str) or any(
        character.isspace() or ord(character) < 32 or ord(character) == 127
        for character in email
    ):
        raise ValueError("email must be a valid email address")
    if email.count("@") != 1:
        raise ValueError("email must be a valid email address")
    local, domain = email.split("@")
    if not local or "." not in domain or not all(domain.split(".")):
        raise ValueError("email must be a valid email address")
    if isinstance(delivery_id, bool) or not isinstance(delivery_id, int) or delivery_id <= 0:
        raise ValueError("delivery_id must be a positive integer")
    return f"Delivery #{delivery_id} is confirmed for {email}."
