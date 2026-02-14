from abc import ABC, abstractmethod
from typing import Any, Dict, List
from software_factory_poc.domain.aggregates.commit_intent import CommitIntent


class VcsDriverPort(ABC):
    @abstractmethod
    async def commit_changes(self, intent: CommitIntent) -> str:
        """[DETERMINISTIC] Executes the commit and returns the hash."""
        pass

    @abstractmethod
    async def get_mcp_tools(self) -> List[Dict[str, Any]]:
        """[AGENTIC] Returns the JSON schemas of the MCP tools."""
        pass

    @abstractmethod
    async def execute_tool(self, tool_name: str, arguments: dict) -> Any:
        """[AGENTIC] Secure proxy for running VCS MCP tools."""
        pass