from abc import ABC, abstractmethod
from typing import Any, Dict, List
from software_factory_poc.domain.aggregates.commit_intent import CommitIntent
from software_factory_poc.domain.aggregates.code_review_report import CodeReviewReport


class VcsDriverPort(ABC):
    @abstractmethod
    async def commit_changes(self, intent: CommitIntent) -> str:
        """[DETERMINISTIC] Executes the commit and returns the hash."""
        pass

    @abstractmethod
    async def get_merge_request_diff(self, mr_id: str) -> str:
        """[DETERMINISTIC] Extracts the diff procedurally via MCP."""
        pass

    @abstractmethod
    async def publish_review(self, mr_id: str, report: CodeReviewReport) -> None:
        """[DETERMINIST] Posts comments online and approves/rejects the MR via MCP."""
        pass

    @abstractmethod
    async def get_mcp_tools(self) -> List[Dict[str, Any]]:
        """[AGENTIC] Returns the JSON schemas of the MCP tools."""
        pass

    @abstractmethod
    async def execute_tool(self, tool_name: str, arguments: dict) -> Any:
        """[AGENTIC] Secure proxy for running VCS MCP tools."""
        pass
