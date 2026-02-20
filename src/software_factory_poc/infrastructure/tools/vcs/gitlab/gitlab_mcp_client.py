"""MCP-stdio client that translates Domain intent into GitLab MCP tool calls."""

import json
import os
from typing import Any

import structlog
from mcp.client.stdio import StdioServerParameters

from software_factory_poc.core.application.tools import VcsTool
from software_factory_poc.core.application.tools.common.exceptions import ProviderError
from software_factory_poc.core.domain.delivery import CommitIntent, FileChangesDTO, FileContent
from software_factory_poc.core.domain.quality import CodeReviewReport
from software_factory_poc.infrastructure.tools.common.base_mcp_client import BaseMcpClient
from software_factory_poc.infrastructure.tools.vcs.gitlab.config.gitlab_settings import (
    GitLabSettings,
)
from software_factory_poc.infrastructure.tools.vcs.gitlab.gitlab_diff_parser import (
    parse_changes_from_diff,
)
from software_factory_poc.infrastructure.tools.vcs.gitlab.gitlab_review_publisher import (
    GitLabReviewPublisher,
)
from software_factory_poc.infrastructure.tools.vcs.gitlab.gitlab_tree_helpers import (
    build_tree_string,
    filter_relevant_paths,
)

logger = structlog.get_logger()

_MAX_FILE_CHARS: int = 25_000


class GitlabMcpClient(BaseMcpClient, VcsTool):
    """Thin MCP client: inherits lifecycle from BaseMcpClient, delegates to helpers."""

    _PROVIDER: str = "GitLabMCP"
    _METRICS_LABEL: str = "gitlab"

    def __init__(self, settings: GitLabSettings) -> None:
        super().__init__()
        self._settings = settings
        self._project_id = settings.project_id

    def _server_params(self) -> StdioServerParameters:
        """Build StdioServerParameters with credentials injected into the subprocess env."""
        env = os.environ.copy()
        if self._settings.token:
            env["GITLAB_PERSONAL_ACCESS_TOKEN"] = self._settings.token.get_secret_value()
        env["GITLAB_API_URL"] = self._settings.base_url
        return StdioServerParameters(
            command=self._settings.mcp_gitlab_command,
            args=self._settings.mcp_gitlab_args,
            env=env,
        )

    # ── Scaffolding Flow Operations ──

    async def validate_branch_existence(self, branch_name: str) -> bool:
        logger.info("Checking branch existence", branch=branch_name, source_system="GitLabMCP")
        try:
            await self._invoke_tool(
                "gitlab_get_branch",
                {"project_id": self._project_id, "branch": branch_name},
            )
            return True
        except ProviderError:
            return False

    async def create_branch(self, branch_name: str, ref: str = "main") -> str:
        logger.info("Creating branch", branch=branch_name, ref=ref, source_system="GitLabMCP")
        result = await self._invoke_tool(
            "gitlab_create_branch",
            {"project_id": self._project_id, "branch": branch_name, "ref": ref},
        )
        raw = self._extract_text(result)
        try:
            return str(json.loads(raw).get("web_url", ""))
        except (json.JSONDecodeError, TypeError):
            return raw

    async def create_merge_request(
        self, source_branch: str, target_branch: str, title: str, description: str
    ) -> str:
        logger.info(
            "Creating merge request",
            source_branch=source_branch,
            target_branch=target_branch,
            source_system="GitLabMCP",
        )
        result = await self._invoke_tool(
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
            return str(json.loads(raw).get("web_url", ""))
        except (json.JSONDecodeError, TypeError):
            return raw

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
        result = await self._invoke_tool(
            "gitlab_create_commit",
            {
                "project_id": self._project_id,
                "branch": intent.branch.value,
                "commit_message": intent.message,
                "actions": actions,
            },
        )
        return str(json.loads(self._extract_text(result)).get("commit_hash", ""))

    # ── Code Review Flow Operations ──

    async def validate_merge_request_existence(self, mr_iid: str) -> bool:
        mr_iid = _extract_iid(mr_iid)
        logger.info("Validating MR existence", mr_iid=mr_iid, source_system="GitLabMCP")
        try:
            result = await self._invoke_tool(
                "gitlab_get_merge_request",
                {"project_id": self._project_id, "merge_request_iid": mr_iid},
            )
            mr_json = json.loads(self._extract_text(result))
            return mr_json.get("state", "") in {"opened", "open"}
        except ProviderError:
            return False

    async def get_repository_tree(self, project_id: str, branch: str) -> str:
        logger.info("Fetching repository tree", branch=branch, source_system="GitLabMCP")
        entries = await self._list_tree_entries(project_id, branch)
        relevant = filter_relevant_paths(entries)
        return build_tree_string(relevant)

    async def get_original_branch_code(self, project_id: str, branch: str) -> list[FileContent]:
        logger.info("Fetching branch code", branch=branch, source_system="GitLabMCP")
        entries = await self._list_tree_entries(project_id, branch)
        relevant = filter_relevant_paths(entries)
        return await self._fetch_file_contents(project_id, branch, relevant)

    async def get_updated_code_diff(self, mr_iid: str) -> list[FileChangesDTO]:
        mr_iid = _extract_iid(mr_iid)
        result = await self._invoke_tool(
            "gitlab_get_merge_request_changes",
            {"project_id": self._project_id, "merge_request_iid": mr_iid},
        )
        return parse_changes_from_diff(self._extract_text(result))

    async def publish_review(self, mr_id: str, report: CodeReviewReport) -> None:
        mr_id = _extract_iid(mr_id)
        publisher = GitLabReviewPublisher(self._invoke_tool, self._project_id)
        await publisher.publish_review(mr_id, report)

    # ── Agentic Operations ──

    async def get_mcp_tools(self) -> list[dict[str, Any]]:
        response = await self._list_tools_response()
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name.replace("gitlab_", "vcs_"),
                    "description": t.description or "",
                    "parameters": t.inputSchema or {},
                },
            }
            for t in response.tools
            if t.name.startswith("gitlab_")
        ]

    async def execute_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        real_tool_name = tool_name.replace("vcs_", "gitlab_")
        if "project_id" not in arguments:
            arguments["project_id"] = self._project_id
        safe_args = self._redactor.sanitize(arguments)
        result = await self._invoke_tool(real_tool_name, safe_args)
        return self._extract_text(result)

    # ── Private helpers ──

    async def _list_tree_entries(self, project_id: str, branch: str) -> list[dict[str, str]]:
        result = await self._invoke_tool(
            "gitlab_list_repository_tree",
            {"project_id": project_id, "ref": branch, "recursive": True},
        )
        raw = self._extract_text(result)
        try:
            entries = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return []
        return [e for e in entries if e.get("type") == "blob"]

    async def _fetch_file_contents(
        self, project_id: str, branch: str, paths: list[str]
    ) -> list[FileContent]:
        files: list[FileContent] = []
        for path in paths:
            try:
                result = await self._invoke_tool(
                    "gitlab_get_file_contents",
                    {"project_id": project_id, "file_path": path, "ref": branch},
                )
                content = self._extract_text(result)
                content = _truncate_content(content, path)
                files.append(FileContent(path=path, content=content, is_new=False))
            except ProviderError:
                logger.debug("Skipping unreadable file", file_path=path, source_system="GitLabMCP")
        return files


# ── Module-level pure functions ──


def _extract_iid(mr_url_or_id: str) -> str:
    """Extract the MR IID from a URL or return a plain number."""
    if "merge_requests/" in mr_url_or_id:
        return mr_url_or_id.split("merge_requests/")[-1].split("/")[0].split("?")[0]
    return mr_url_or_id.strip()


def _truncate_content(content: str, path: str) -> str:
    """Truncate file content exceeding _MAX_FILE_CHARS to prevent token overflow."""
    if len(content) <= _MAX_FILE_CHARS:
        return content
    logger.warning(
        "File content truncated",
        file_path=path,
        original_chars=len(content),
        max_chars=_MAX_FILE_CHARS,
        source_system="GitLabMCP",
    )
    return content[:_MAX_FILE_CHARS] + (
        "\n\n...[CONTENIDO TRUNCADO POR SEGURIDAD DE VENTANA DE CONTEXTO]"
    )
