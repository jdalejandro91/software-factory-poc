from abc import ABC, abstractmethod

class LLMError(Exception):
    """Raised when LLM generation fails."""
    pass

class LLMGatewayPort(ABC):
    @abstractmethod
    def generate_code(self, prompt: str, model: str) -> str:
        """Generates code using the specified model."""
        pass
