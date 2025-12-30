from dataclasses import dataclass


@dataclass
class RetryableError(Exception):
    message: str
    original_exception: Exception | None = None

    def __str__(self):
        return f"RetryableError: {self.message}"
