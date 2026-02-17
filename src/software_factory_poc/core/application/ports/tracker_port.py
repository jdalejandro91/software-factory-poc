from abc import ABC, abstractmethod
from typing import Any

from software_factory_poc.core.domain.mission import Mission
from software_factory_poc.core.domain.quality import CodeReviewReport


class TrackerPort(ABC):
    @abstractmethod
    async def get_task(self, ticket_id: str) -> Mission:
        pass

    @abstractmethod
    async def update_status(self, ticket_id: str, status: str) -> None:
        pass

    @abstractmethod
    async def update_task_description(self, ticket_id: str, description: str) -> None:
        pass

    @abstractmethod
    async def post_review_summary(self, ticket_id: str, report: CodeReviewReport) -> None:
        pass

    @abstractmethod
    async def add_comment(self, ticket_id: str, comment: str) -> None:
        pass

    @abstractmethod
    async def get_mcp_tools(self) -> list[dict[str, Any]]:
        pass

    @abstractmethod
    async def execute_tool(self, tool_name: str, arguments: dict) -> Any:
        pass
