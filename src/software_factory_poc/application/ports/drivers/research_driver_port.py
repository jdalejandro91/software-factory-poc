from abc import ABC, abstractmethod

class ResearchDriverPort(ABC):
    @abstractmethod
    async def get_architecture_context(self, project_context_id: str) -> str:
        pass