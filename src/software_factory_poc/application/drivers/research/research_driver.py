from abc import ABC, abstractmethod

class ResearchDriverPort(ABC):
    @abstractmethod
    async def get_project_context(self, service_name: str) -> str:
        pass

    @abstractmethod
    async def get_architecture_context(self, project_context_id: str) -> str:
        pass