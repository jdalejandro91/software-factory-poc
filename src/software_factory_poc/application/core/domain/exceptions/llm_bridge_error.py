from __future__ import annotations


from software_factory_poc.application.core.domain.exceptions.infra_error import InfraError

class LlmBridgeError(InfraError):
    """Base error for llm-bridge."""
