from abc import abstractmethod
from typing import Any

from software_factory_poc.core.domain.delivery import CommitIntent, FileChangesDTO, FileContent
from software_factory_poc.core.domain.quality import CodeReviewReport
from software_factory_poc.core.domain.shared.base_tool import BaseTool
from software_factory_poc.core.domain.shared.tool_type import ToolType


class VcsTool(BaseTool):
    """Abstract tool contract for Version Control System interactions."""

    @property
    def tool_type(self) -> ToolType:
        return ToolType.VCS

    # ── Deterministic Operations (Scaffolding Flow) ──

    @abstractmethod
    async def validate_branch_existence(self, branch_name: str) -> bool:
        """Checks if a branch exists. Returns True if it does."""

    @abstractmethod
    async def create_branch(self, branch_name: str, ref: str = "main") -> str:
        """Creates a new branch from ref. Returns the branch URL."""

    @abstractmethod
    async def commit_changes(self, intent: CommitIntent) -> str:
        """Executes the commit and returns the hash."""

    @abstractmethod
    async def create_merge_request(
        self, source_branch: str, target_branch: str, title: str, description: str
    ) -> str:
        """Creates a merge request. Returns the MR web URL."""

    # ── Deterministic Operations (Code Review Flow) ──

    @abstractmethod
    async def validate_merge_request_existence(self, mr_iid: str) -> bool:
        """Check if the MR exists and is open. Returns False if not found or closed."""

    @abstractmethod
    async def get_repository_tree(self, project_id: str, branch: str) -> str:
        """Return a filtered directory skeleton (no file content) as a formatted string.

        The LLM uses this lightweight listing as a mental map of the project
        structure without consuming tokens on full file contents.
        """

    @abstractmethod
    async def get_original_branch_code(self, project_id: str, branch: str) -> list[FileContent]:
        """Retrieve file contents from a branch (tree + content for relevant files)."""

    @abstractmethod
    async def get_updated_code_diff(self, mr_iid: str) -> list[FileChangesDTO]:
        """Retrieve structured diff for a Merge Request with hunks and line numbers."""

    @abstractmethod
    async def publish_review(self, mr_id: str, report: CodeReviewReport) -> None:
        """Posts comments online and approves/rejects the MR via MCP."""

    # ── Agentic Operations ──

    @abstractmethod
    async def get_mcp_tools(self) -> list[dict[str, Any]]:
        """Returns the JSON schemas of the MCP tools."""

    @abstractmethod
    async def execute_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        """Secure proxy for running VCS MCP tools."""
