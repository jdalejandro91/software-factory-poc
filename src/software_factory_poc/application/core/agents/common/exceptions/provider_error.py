from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from software_factory_poc.application.core.agents.common.exceptions.infra_error import InfraError


@dataclass(frozen=False)
class ProviderError(InfraError):
    provider: str
    message: str
    retryable: bool = False
    status_code:Optional[ int] = None
    error_code:Optional[ str] = None

    def __str__(self) -> str:
        code = f" status={self.status_code}" if self.status_code is not None else ""
    def __str__(self) -> str:
        code = f" status={self.status_code}" if self.status_code is not None else ""
        return f"{self.provider}: {self.message}{code}"
