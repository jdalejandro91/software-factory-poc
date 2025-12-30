from abc import ABC, abstractmethod


class KnowledgeBasePort(ABC):
    @abstractmethod
    def get_knowledge(self, url: str) -> str:
        """Retrieve knowledge context from a given URL."""
        pass
