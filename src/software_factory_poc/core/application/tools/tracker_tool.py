from abc import abstractmethod
from typing import Any

from software_factory_poc.core.domain.shared.base_tool import BaseTool
from software_factory_poc.core.domain.shared.tool_type import ToolType


class TrackerTool(BaseTool):
    """Abstract tool contract for Task Tracker interactions."""

    @property
    def tool_type(self) -> ToolType:
        return ToolType.TRACKER

    @abstractmethod
    async def update_status(self, ticket_id: str, status: str) -> None: ...

    @abstractmethod
    async def update_task_description(self, ticket_id: str, appended_text: str) -> None: ...

    @abstractmethod
    async def add_comment(self, ticket_id: str, comment: str) -> None: ...

    @abstractmethod
    async def get_mcp_tools(self) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def execute_tool(self, name: str, arguments: dict[str, Any]) -> Any: ...
