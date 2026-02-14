from dataclasses import dataclass

from software_factory_poc.application.ports.drivers.common.exceptions.retryable_error import RetryableError


@dataclass
class AllModelsExhaustedException(RetryableError):
    """Raised when all configured LLM models/providers have failed."""
    def __str__(self):
        return f"AllModelsExhaustedException: {self.message}"
