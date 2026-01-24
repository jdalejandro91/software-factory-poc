from abc import ABC, abstractmethod
from typing import Optional

class KnowledgeAgent(ABC):
    """
    Domain Entity/Service responsible for technical context extraction.
    """

    @abstractmethod
    def extract_context(self, search_criteria: dict) -> str:
        """
        Extracts technical knowledge based on criteria.
        """
        pass

    @abstractmethod
    def validate_context(self, context: str) -> bool:
        """
        Validates if the retrieved context is sufficient/valid.
        """
        pass
