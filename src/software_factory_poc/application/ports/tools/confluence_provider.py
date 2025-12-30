from abc import ABC, abstractmethod


class ConfluenceProvider(ABC):
    """Abstract base class for Confluence operations."""

    @abstractmethod
    def get_page_content(self, page_id: str) -> str:
        """Retrieves the content of a Confluence page."""
        pass
