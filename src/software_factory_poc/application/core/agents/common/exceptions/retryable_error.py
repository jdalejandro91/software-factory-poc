from typing import Optional
from dataclasses import dataclass


@dataclass
class RetryableError(Exception):
    message: str
    original_exception:Optional[ Exception] = None

    def __str__(self):
        return f"RetryableError: {self.message}"
