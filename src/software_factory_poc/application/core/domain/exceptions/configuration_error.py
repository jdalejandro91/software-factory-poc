from __future__ import annotations

from software_factory_poc.application.core.domain.exceptions.llm_bridge_error import LlmBridgeError


class ConfigurationError(LlmBridgeError):
    """Raised when configuration is invalid or incomplete."""
