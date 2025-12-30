import time
from datetime import UTC, datetime


def now_utc_iso() -> str:
    """
    Returns current UTC timestamp in ISO 8601 format (with Z suffix).
    """
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")

def monotonic_ms() -> float:
    """
    Returns monotonic time in milliseconds.
    """
    return time.monotonic() * 1000
