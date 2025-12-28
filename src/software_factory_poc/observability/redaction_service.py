import re
from typing import Any

# Regex patterns for common secrets
SECRET_PATTERNS = [
    r"(Bearer\s+)([a-zA-Z0-9\-\._~+/=]+)",
    r"(Private-Token:\s*)([a-zA-Z0-9\-\._~+/=]+)",
    r"(Authorization:\s*)([a-zA-Z0-9\-\._~+/=]+)",
    r"(api_token\s*[:=]\s*)(['\"]?[a-zA-Z0-9\-\._~+/=]+['\"]?)",
]

SENSITIVE_KEYS = {
    "authorization",
    "private-token",
    "api_token",
    "token",
    "password",
    "secret",
    "client_secret",
}

def redact_text(text: str) -> str:
    """
    Redacts secrets from a string using regex patterns.
    """
    if not text:
        return text
        
    redacted_text = text
    for pattern in SECRET_PATTERNS:
        # Replace the captured group 2 (the secret) with [REDACTED]
        # Regex structure assumes (prefix)(secret)
        redacted_text = re.sub(pattern, r"\1[REDACTED]", redacted_text, flags=re.IGNORECASE)
    
    return redacted_text

def redact_value(value: Any) -> Any:
    """
    Recursive helper to redact values in dicts/lists.
    """
    if isinstance(value, str):
        return redact_text(value)
    elif isinstance(value, dict):
        return redact_dict(value)
    elif isinstance(value, list):
        return [redact_value(item) for item in value]
    return value

def redact_dict(obj: dict[str, Any]) -> dict[str, Any]:
    """
    Redacts sensitive keys and values in a dictionary (recursive).
    """
    new_obj = {}
    for k, v in obj.items():
        key_lower = str(k).lower()
        if any(sensitive in key_lower for sensitive in SENSITIVE_KEYS):
            new_obj[k] = "[REDACTED]"
        else:
            new_obj[k] = redact_value(v)
    return new_obj
