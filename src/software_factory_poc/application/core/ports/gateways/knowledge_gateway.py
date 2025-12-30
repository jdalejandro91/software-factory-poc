from abc import ABC, abstractmethod


class KnowledgeGateway(ABC):
    @abstractmethod
    def retrieve_context(self, criteria: dict) -> str:
        """
        Retrieves relevant context based on search criteria.
        """
        raise NotImplementedError
