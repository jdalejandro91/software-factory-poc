from __future__ import annotations

from software_factory_poc.core.exceptions.llm_bridge_error import LlmBridgeError


class DependencyError(LlmBridgeError):
    """Raised when an optional provider dependency is missing."""
