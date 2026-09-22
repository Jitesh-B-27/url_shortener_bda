import secrets
import string
from urllib.parse import urlparse

ALPHABET = string.ascii_letters + string.digits
CODE_LENGTH = 7
MAX_URL_LENGTH = 2048


def validate_url(value):
    url = (value or "").strip()
    if not url:
        return None, "Please enter a URL."
    if len(url) > MAX_URL_LENGTH:
        return None, "The URL is too long."
    try:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError
        if any(char.isspace() for char in parsed.netloc):
            raise ValueError
        _ = parsed.port
    except (TypeError, ValueError):
        return None, "Enter a valid URL beginning with http:// or https://."
    return url, None


def generate_short_code(length=CODE_LENGTH):
    return "".join(secrets.choice(ALPHABET) for _ in range(length))
