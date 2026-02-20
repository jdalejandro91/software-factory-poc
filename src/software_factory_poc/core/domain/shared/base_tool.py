from abc import ABC, abstractmethod
from typing import Any

from software_factory_poc.core.domain.shared.tool_type import ToolType


class BaseTool(ABC):
    """Domain-level contract every external tool adapter must satisfy."""

    @property
    @abstractmethod
    def tool_type(self) -> ToolType: ...

    async def connect(self) -> None:
        """Open a persistent connection (no-op by default; MCP clients override)."""
        return

    async def disconnect(self) -> None:
        """Close the persistent connection (no-op by default; MCP clients override)."""
        return

    async def get_mcp_tools(self) -> list[dict[str, Any]]:
        return []

    async def execute_tool(self, name: str, arguments: dict[str, Any]) -> Any:  # noqa: ARG002
        return None
