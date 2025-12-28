from __future__ import annotations

from llm_bridge.core.exceptions.llm_bridge_error import LlmBridgeError


class ConfigurationError(LlmBridgeError):
    """Raised when configuration is invalid or incomplete."""
