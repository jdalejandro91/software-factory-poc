from __future__ import annotations

from dataclasses import dataclass

from software_factory_poc.core.application.tools.common.exceptions.provider_error import (
    ProviderError,
)


@dataclass(frozen=False)
class ProviderNotSupportedError(ProviderError):
    """Raised when a VCS/tracker provider is not supported by the platform."""

    def __init__(self, provider: str) -> None:
        super().__init__(
            provider=provider,
            message=f"Provider '{provider}' is not supported.",
            retryable=False,
        )

    def __str__(self) -> str:
        return f"ProviderNotSupportedError: {self.message}"
