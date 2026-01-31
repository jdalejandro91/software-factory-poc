from dataclasses import dataclass
from typing import Optional


@dataclass
class RetryableError(Exception):
    message: str
    original_exception:Optional[ Exception] = None

    def __str__(self):
        return f"RetryableError: {self.message}"
