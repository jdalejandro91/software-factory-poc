from abc import ABC, abstractmethod
from typing import Any

from software_factory_poc.core.domain.delivery.commit_intent import CommitIntent
from software_factory_poc.core.domain.quality.code_review_report import CodeReviewReport


class VcsPort(ABC):

    # ── Deterministic Operations (Scaffolding Flow) ──

    @abstractmethod
    async def validate_branch_existence(self, branch_name: str) -> bool:
        """[DETERMINISTIC] Checks if a branch exists. Returns True if it does."""
        pass

    @abstractmethod
    async def create_branch(self, branch_name: str, ref: str = "main") -> str:
        """[DETERMINISTIC] Creates a new branch from ref. Returns the branch URL."""
        pass

    @abstractmethod
    async def commit_changes(self, intent: CommitIntent) -> str:
        """[DETERMINISTIC] Executes the commit and returns the hash."""
        pass

    @abstractmethod
    async def create_merge_request(
        self, source_branch: str, target_branch: str, title: str, description: str
    ) -> str:
        """[DETERMINISTIC] Creates a merge request. Returns the MR web URL."""
        pass

    # ── Deterministic Operations (Code Review Flow) ──

    @abstractmethod
    async def get_merge_request_diff(self, mr_id: str) -> str:
        """[DETERMINISTIC] Extracts the diff procedurally via MCP."""
        pass

    @abstractmethod
    async def publish_review(self, mr_id: str, report: CodeReviewReport) -> None:
        """[DETERMINISTIC] Posts comments online and approves/rejects the MR via MCP."""
        pass

    # ── Agentic Operations ──

    @abstractmethod
    async def get_mcp_tools(self) -> list[dict[str, Any]]:
        """[AGENTIC] Returns the JSON schemas of the MCP tools."""
        pass

    @abstractmethod
    async def execute_tool(self, tool_name: str, arguments: dict) -> Any:
        """[AGENTIC] Secure proxy for running VCS MCP tools."""
        pass
