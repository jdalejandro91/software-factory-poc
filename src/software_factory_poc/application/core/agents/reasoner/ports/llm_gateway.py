from abc import ABC, abstractmethod

from software_factory_poc.application.core.agents.common.value_objects.model_id import ModelId
from software_factory_poc.application.core.agents.reasoner.llm_response import LlmResponse


class LLMError(Exception):
    """Base exception for LLM Gateway errors."""
    pass


class LlmGateway(ABC):
    @abstractmethod
    def generate_code(
        self, 
        prompt: str, 
        context: str, 
        model_hints: list[ModelId]
    ) -> LlmResponse:
        """
        Generates code based on the prompt and context, trying models specified in hints.
        """
        raise NotImplementedError
