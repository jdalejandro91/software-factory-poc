from abc import ABC, abstractmethod


class ContextRetrievalPort(ABC):
    @abstractmethod
    def get_knowledge(self, url: str) -> str:
        """Retrieve knowledge context from a given URL."""
        pass
