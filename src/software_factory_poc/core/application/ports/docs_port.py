from abc import ABC, abstractmethod
from typing import Any


class DocsPort(ABC):
    @abstractmethod
    async def get_project_context(self, service_name: str) -> str:
        pass

    @abstractmethod
    async def get_architecture_context(self, project_context_id: str) -> str:
        pass

    # ── Agentic Operations ──

    @abstractmethod
    async def get_mcp_tools(self) -> list[dict[str, Any]]:
        """[AGENTIC] Returns the JSON schemas of the MCP tools."""

    @abstractmethod
    async def execute_tool(self, tool_name: str, arguments: dict[str, Any]) -> str:
        """[AGENTIC] Secure proxy for running Docs MCP tools."""
