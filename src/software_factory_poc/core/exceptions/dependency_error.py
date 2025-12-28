from __future__ import annotations

from llm_bridge.core.exceptions.llm_bridge_error import LlmBridgeError


class DependencyError(LlmBridgeError):
    """Raised when an optional provider dependency is missing."""
