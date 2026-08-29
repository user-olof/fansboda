"""Parse and normalize ALLOWED_EMAILS configuration."""


def parse_allowed_emails(value):
    """
    Parse ALLOWED_EMAILS from a semicolon-separated string or a list.

    Examples:
        "a@x.com;b@x.com" -> ["a@x.com", "b@x.com"]
        ["a@x.com", "b@x.com"] -> ["a@x.com", "b@x.com"]
    """
    if value is None:
        return []

    if isinstance(value, str):
        parts = value.split(";")
    elif isinstance(value, (list, tuple, set)):
        parts = value
    else:
        parts = [value]

    emails = []
    for part in parts:
        if part is None:
            continue
        email = str(part).strip()
        if email:
            emails.append(email)
    return emails


def normalized_allowed_email_set(value):
    """Return a lowercase set of allowed emails."""
    return {email.lower() for email in parse_allowed_emails(value)}
