import json
import logging
import os
from typing import Any

from mcp import McpError
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from software_factory_poc.core.application.ports.common.exceptions.provider_error import (
    ProviderError,
)
from software_factory_poc.core.application.ports.vcs_port import VcsPort
from software_factory_poc.core.domain.delivery.commit_intent import CommitIntent
from software_factory_poc.core.domain.quality.code_review_report import CodeReviewReport
from software_factory_poc.infrastructure.observability.redaction_service import RedactionService
from software_factory_poc.infrastructure.tools.vcs.gitlab.config.gitlab_settings import (
    GitLabSettings,
)

logger = logging.getLogger(__name__)


class GitlabMcpClient(VcsPort):
    """MCP-stdio client that translates Domain intent into GitLab MCP tool calls."""

    def __init__(self, settings: GitLabSettings, redactor: RedactionService) -> None:
        self._settings = settings
        self._redactor = redactor
        self._project_id = settings.project_id

    # ── MCP connection internals ──

    def _server_params(self) -> StdioServerParameters:
        """Build StdioServerParameters with credentials injected into the subprocess env."""
        env = {**os.environ}
        if self._settings.token:
            env["GITLAB_TOKEN"] = self._settings.token.get_secret_value()
        env["GITLAB_BASE_URL"] = self._settings.base_url
        return StdioServerParameters(
            command=self._settings.mcp_gitlab_command,
            args=self._settings.mcp_gitlab_args,
            env=env,
        )

    async def _call_mcp(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Open an stdio MCP session, invoke the tool, and translate errors."""
        try:
            async with stdio_client(self._server_params()) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(tool_name, arguments=arguments)
        except McpError as exc:
            raise ProviderError(
                provider="GitLabMCP",
                message=f"MCP protocol error invoking '{tool_name}': {exc}",
                retryable=True,
            ) from exc
        except Exception as exc:
            raise ProviderError(
                provider="GitLabMCP",
                message=f"Connection failure invoking '{tool_name}': {exc}",
                retryable=True,
            ) from exc

        if result.isError:
            error_detail = self._extract_text(result) or "No detail"
            raise ProviderError(
                provider="GitLabMCP",
                message=f"Tool '{tool_name}' returned error: {error_detail}",
                retryable=False,
            )

        return result

    @staticmethod
    def _extract_text(result: Any) -> str:
        """Extract plain text from an MCP CallToolResult safely."""
        if result.content and len(result.content) > 0:
            first = result.content[0]
            return getattr(first, "text", str(first))
        return ""

    # ── Scaffolding Flow Operations ──

    async def validate_branch_existence(self, branch_name: str) -> bool:
        logger.info("[GitLabMCP] Checking branch existence: '%s'", branch_name)
        try:
            await self._call_mcp(
                "gitlab_get_branch",
                {"project_id": self._project_id, "branch": branch_name},
            )
            return True
        except ProviderError:
            return False

    async def create_branch(self, branch_name: str, ref: str = "main") -> str:
        logger.info("[GitLabMCP] Creating branch '%s' from '%s'", branch_name, ref)
        result = await self._call_mcp(
            "gitlab_create_branch",
            {"project_id": self._project_id, "branch": branch_name, "ref": ref},
        )
        raw = self._extract_text(result)
        try:
            return json.loads(raw).get("web_url", "")
        except (json.JSONDecodeError, TypeError):
            return raw

    async def create_merge_request(
        self, source_branch: str, target_branch: str, title: str, description: str
    ) -> str:
        logger.info("[GitLabMCP] Creating MR: '%s' → '%s'", source_branch, target_branch)
        result = await self._call_mcp(
            "gitlab_create_merge_request",
            {
                "project_id": self._project_id,
                "source_branch": source_branch,
                "target_branch": target_branch,
                "title": title,
                "description": description,
            },
        )
        raw = self._extract_text(result)
        try:
            return json.loads(raw).get("web_url", "")
        except (json.JSONDecodeError, TypeError):
            return raw

    # ── Commit Operation ──

    async def commit_changes(self, intent: CommitIntent) -> str:
        if intent.is_empty():
            raise ValueError("Commit contains no files.")

        actions = [
            {
                "action": "create" if f.is_new else "update",
                "file_path": f.path,
                "content": f.content,
            }
            for f in intent.files
        ]

        result = await self._call_mcp(
            "gitlab_create_commit",
            {
                "project_id": self._project_id,
                "branch": intent.branch.value,
                "commit_message": intent.message,
                "actions": actions,
            },
        )
        return json.loads(self._extract_text(result)).get("commit_hash", "")

    # ── Code Review Flow Operations ──

    async def get_merge_request_diff(self, mr_id: str) -> str:
        result = await self._call_mcp(
            "gitlab_get_merge_request_changes",
            {"project_id": self._project_id, "merge_request_iid": str(mr_id)},
        )
        return self._extract_text(result)

    async def publish_review(self, mr_id: str, report: CodeReviewReport) -> None:
        status_label = "APPROVED" if report.is_approved else "CHANGES REQUESTED"
        main_note = f"### BrahMAS Code Review: {status_label}\n\n{report.summary}"

        await self._call_mcp(
            "gitlab_create_merge_request_note",
            {
                "project_id": self._project_id,
                "merge_request_iid": str(mr_id),
                "body": main_note,
            },
        )

        for issue in report.comments:
            body = (
                f"**[{issue.severity.value}]** {issue.description}"
                f"\n\n*Suggestion:* `{issue.suggestion}`"
            )
            await self._call_mcp(
                "gitlab_create_merge_request_discussion",
                {
                    "project_id": self._project_id,
                    "merge_request_iid": str(mr_id),
                    "file_path": issue.file_path,
                    "line": issue.line_number if issue.line_number else 1,
                    "body": body,
                },
            )

        if report.is_approved:
            await self._call_mcp(
                "gitlab_approve_merge_request",
                {"project_id": self._project_id, "merge_request_iid": str(mr_id)},
            )

    # ── Agentic Operations ──

    async def get_mcp_tools(self) -> list[dict[str, Any]]:
        async with stdio_client(self._server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                response = await session.list_tools()

        return [
            {
                "name": t.name.replace("gitlab_", "vcs_"),
                "description": t.description,
                "inputSchema": t.inputSchema,
            }
            for t in response.tools
            if t.name.startswith("gitlab_")
        ]

    async def execute_tool(self, tool_name: str, arguments: dict) -> Any:
        real_tool_name = tool_name.replace("vcs_", "gitlab_")
        if "project_id" not in arguments:
            arguments["project_id"] = self._project_id

        safe_args = self._redactor.sanitize(arguments)
        result = await self._call_mcp(real_tool_name, safe_args)
        return self._extract_text(result)
