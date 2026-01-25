from abc import ABC, abstractmethod


class ResearchGateway(ABC):
    @abstractmethod
    def retrieve_context(self, query: str) -> str:
        """
        Retrieves relevant context based on search criteria.
        """
        raise NotImplementedError

    @abstractmethod
    def get_page_content(self, page_id: str) -> str:
        """
        Retrieves content by specific Page ID.
        """
        raise NotImplementedError
