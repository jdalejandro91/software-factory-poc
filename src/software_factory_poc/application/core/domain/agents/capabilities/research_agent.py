from abc import ABC, abstractmethod
from typing import Dict

class ResearchAgent(ABC):
    """
    Capability contract for Agents responsible for Active Investigation.
    Focuses on WHAT: investigating a query to retrieve information.
    """
    
    @abstractmethod
    def investigate(self, query: str, filters: Dict) -> str:
        """
        Performs an investigation based on a query and filters (e.g. searching Confluence, Web).
        Returns the findings as a string (context).
        """
        pass
