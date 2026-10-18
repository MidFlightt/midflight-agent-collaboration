"""Generate local confirmation messages; do not send email."""


def confirmation(email: str, delivery_id: int) -> str:
    """Format a confirmation for a supplied ID using basic email validation.

    This local formatter neither verifies mailbox existence nor fetches delivery
    state. Callers supply the ID of the delivery they have confirmed.
    """
    if not isinstance(email, str) or any(char.isspace() for char in email):
        raise ValueError("email must be a valid email address")
    if email.count("@") != 1:
        raise ValueError("email must be a valid email address")
    local, domain = email.split("@")
    if not local or "." not in domain or not all(domain.split(".")):
        raise ValueError("email must be a valid email address")
    if isinstance(delivery_id, bool) or not isinstance(delivery_id, int) or delivery_id <= 0:
        raise ValueError("delivery_id must be a positive integer")
    return f"Delivery {delivery_id} is confirmed. Confirmation for {email}."
