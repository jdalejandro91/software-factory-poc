from abc import ABC, abstractmethod


class KnowledgeGateway(ABC):
    @abstractmethod
    def retrieve_context(self, query: str) -> str:
        """
        Retrieves relevant context based on a query string.
        """
        raise NotImplementedError
