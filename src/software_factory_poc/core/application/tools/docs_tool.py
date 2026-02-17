from abc import abstractmethod
from typing import Any

from software_factory_poc.core.domain.shared.base_tool import BaseTool
from software_factory_poc.core.domain.shared.tool_type import ToolType


class DocsTool(BaseTool):
    """Abstract tool contract for Documentation/Research interactions."""

    @property
    def tool_type(self) -> ToolType:
        return ToolType.DOCS

    @abstractmethod
    async def get_project_context(self, service_name: str) -> str: ...

    @abstractmethod
    async def get_architecture_context(self, project_context_id: str) -> str: ...

    @abstractmethod
    async def get_mcp_tools(self) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def execute_tool(self, name: str, arguments: dict[str, Any]) -> str: ...
