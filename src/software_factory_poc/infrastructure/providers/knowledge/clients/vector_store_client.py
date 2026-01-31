
import abc
from typing import List, Dict, Any

class VectorStoreClient(abc.ABC):
    """
    Abstract Base Class for Vector Store Operations (RAG Memory).
    Specific implementations (Pinecone, Chroma, etc.) will inherit from this.
    """
    
    @abc.abstractmethod
    def query_knowledge_base(self, query: str) -> List[Dict[str, Any]]:
        """
        Retrieves relevant context from the vector database.
        """
        pass
        
    # TODO: Implement connection logic and embedding generation support.
