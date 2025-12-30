from __future__ import annotations

from dataclasses import dataclass

from software_factory_poc.application.core.domain.exceptions.infra_error import InfraError
@dataclass(frozen=True, slots=True)
class ProviderError(InfraError):
    provider: str
    message: str
    retryable: bool = False
    status_code: int | None = None
    error_code: str | None = None

    def __str__(self) -> str:
        code = f" status={self.status_code}" if self.status_code is not None else ""
    def __str__(self) -> str:
        code = f" status={self.status_code}" if self.status_code is not None else ""
        return f"{self.provider}: {self.message}{code}"
