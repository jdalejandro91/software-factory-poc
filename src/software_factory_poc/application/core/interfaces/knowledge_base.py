from abc import ABC, abstractmethod

class KnowledgeBasePort(ABC):
    @abstractmethod
    def get_architecture_guidelines(self, url: str) -> str:
        """Retrieves architecture guidelines from a knowledge source."""
        pass
