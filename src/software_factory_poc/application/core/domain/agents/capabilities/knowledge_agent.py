from abc import ABC, abstractmethod

class KnowledgeAgent(ABC):
    """
    Capability contract for Agents responsible for Information Retrieval (RAG/Knowledge Base).
    Focuses on WHAT: retrieving existing known solutions or rules.
    """

    @abstractmethod
    def retrieve_similar_solutions(self, topic: str) -> str:
        """
        Retrieves similar solutions or architectural patterns related to a topic.
        """
        pass
