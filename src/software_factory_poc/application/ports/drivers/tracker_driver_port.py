from abc import ABC, abstractmethod

class TrackerDriverPort(ABC):
    @abstractmethod
    async def get_task_description(self, ticket_id: str) -> str:
        pass

    @abstractmethod
    async def update_status(self, ticket_id: str, status: str) -> None:
        pass

    @abstractmethod
    async def add_comment(self, ticket_id: str, comment: str) -> None:
        pass