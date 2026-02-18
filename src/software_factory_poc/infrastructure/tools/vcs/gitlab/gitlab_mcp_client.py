import json
import logging
import os
import re
from typing import Any

from mcp import McpError
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from software_factory_poc.core.application.tools import VcsTool
from software_factory_poc.core.application.tools.common.exceptions import ProviderError
from software_factory_poc.core.domain.delivery import CommitIntent, FileChangesDTO, FileContent
from software_factory_poc.core.domain.quality import CodeReviewReport
from software_factory_poc.infrastructure.observability.redaction_service import RedactionService
from software_factory_poc.infrastructure.tools.vcs.gitlab.config.gitlab_settings import (
    GitLabSettings,
)

logger = logging.getLogger(__name__)

_HUNK_HEADER_RE = re.compile(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@", re.MULTILINE)

_IGNORED_DIRS = frozenset(
    {
        "node_modules",
        ".git",
        "__pycache__",
        ".mypy_cache",
        ".ruff_cache",
        "dist",
        "build",
        ".venv",
        "venv",
        ".tox",
        ".eggs",
        ".pytest_cache",
    }
)
_BINARY_EXTENSIONS = frozenset(
    {
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".ico",
        ".svg",
        ".webp",
        ".woff",
        ".woff2",
        ".ttf",
        ".eot",
        ".otf",
        ".pdf",
        ".zip",
        ".gz",
        ".tar",
        ".jar",
        ".war",
        ".class",
        ".pyc",
        ".so",
        ".dll",
        ".exe",
        ".bin",
        ".lock",
        ".map",
    }
)
_MAX_BRANCH_FILES = 50


class GitlabMcpClient(VcsTool):
    """MCP-stdio client that translates Domain intent into GitLab MCP tool calls."""

    def __init__(self, settings: GitLabSettings) -> None:
        self._settings = settings
        self._project_id = settings.project_id
        self._redactor = RedactionService()

    # ── MCP connection internals ──

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

    async def _invoke_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
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
            await self._invoke_tool(
                "gitlab_get_branch",
                {"project_id": self._project_id, "branch": branch_name},
            )
            return True
        except ProviderError:
            return False

    async def create_branch(self, branch_name: str, ref: str = "main") -> str:
        logger.info("[GitLabMCP] Creating branch '%s' from '%s'", branch_name, ref)
        result = await self._invoke_tool(
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

        result = await self._invoke_tool(
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

    async def validate_merge_request_existence(self, mr_iid: str) -> bool:
        """Check if the MR exists and is open via MCP."""
        logger.info("[GitLabMCP] Validating MR existence: iid=%s", mr_iid)
        try:
            result = await self._invoke_tool(
                "gitlab_get_merge_request",
                {"project_id": self._project_id, "merge_request_iid": str(mr_iid)},
            )
            data = json.loads(self._extract_text(result))
            return data.get("state", "") in {"opened", "open"}
        except ProviderError:
            return False

    async def get_original_branch_code(self, project_id: str, branch: str) -> list[FileContent]:
        """List repository tree and fetch content for relevant files."""
        logger.info("[GitLabMCP] Fetching branch code for '%s' (project=%s)", branch, project_id)
        entries = await self._list_tree_entries(project_id, branch)
        relevant = self._filter_relevant_paths(entries)
        return await self._fetch_file_contents(project_id, branch, relevant)

    async def get_updated_code_diff(self, mr_iid: str) -> list[FileChangesDTO]:
        """Retrieve structured diff with parsed hunks and line numbers."""
        result = await self._invoke_tool(
            "gitlab_get_merge_request_changes",
            {"project_id": self._project_id, "merge_request_iid": str(mr_iid)},
        )
        raw = self._extract_text(result)
        return self._parse_mr_changes(raw)

    async def get_merge_request_diff(self, mr_id: str) -> str:
        """Retrieve raw unified diff text (agentic / legacy use)."""
        result = await self._invoke_tool(
            "gitlab_get_merge_request_changes",
            {"project_id": self._project_id, "merge_request_iid": str(mr_id)},
        )
        return self._extract_text(result)

    # ── Branch Code Helpers ──

    async def _list_tree_entries(self, project_id: str, branch: str) -> list[dict[str, str]]:
        """List all blob entries in the repository tree."""
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

    @staticmethod
    def _filter_relevant_paths(entries: list[dict[str, str]]) -> list[str]:
        """Exclude binary files and irrelevant directories."""
        paths: list[str] = []
        for entry in entries:
            path = entry.get("path", "")
            if any(segment in _IGNORED_DIRS for segment in path.split("/")):
                continue
            if any(path.endswith(ext) for ext in _BINARY_EXTENSIONS):
                continue
            paths.append(path)
        return paths[:_MAX_BRANCH_FILES]

    async def _fetch_file_contents(
        self, project_id: str, branch: str, paths: list[str]
    ) -> list[FileContent]:
        """Fetch actual content for each file path via MCP."""
        files: list[FileContent] = []
        for path in paths:
            try:
                result = await self._invoke_tool(
                    "gitlab_get_file_contents",
                    {"project_id": project_id, "file_path": path, "ref": branch},
                )
                content = self._extract_text(result)
                files.append(FileContent(path=path, content=content, is_new=False))
            except ProviderError:
                logger.debug("[GitLabMCP] Skipping unreadable file: %s", path)
        return files

    # ── Diff Parsing Helpers ──

    @staticmethod
    def _parse_mr_changes(raw: str) -> list[FileChangesDTO]:
        """Parse the MCP response from gitlab_get_merge_request_changes."""
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return []
        changes = data.get("changes", data) if isinstance(data, dict) else data
        if not isinstance(changes, list):
            return []
        return [
            GitlabMcpClient._parse_single_change(change)
            for change in changes
            if isinstance(change, dict)
        ]

    @staticmethod
    def _parse_single_change(change: dict[str, str]) -> FileChangesDTO:
        """Parse a single file change entry into a FileChangesDTO."""
        diff_text = change.get("diff", "")
        hunks, added, removed = GitlabMcpClient._parse_diff_hunks(diff_text)
        return FileChangesDTO(
            old_path=change.get("old_path"),
            new_path=change.get("new_path", ""),
            hunks=hunks,
            added_lines=added,
            removed_lines=removed,
        )

    @staticmethod
    def _parse_diff_hunks(diff_text: str) -> tuple[list[str], list[int], list[int]]:
        """Extract hunks, added line numbers, and removed line numbers from unified diff."""
        if not diff_text:
            return [], [], []
        hunks: list[str] = []
        added_lines: list[int] = []
        removed_lines: list[int] = []
        parts = _HUNK_HEADER_RE.split(diff_text)
        for i in range(1, len(parts), 3):
            old_start = int(parts[i])
            new_start = int(parts[i + 1])
            body = parts[i + 2] if i + 2 < len(parts) else ""
            hunks.append(f"@@ -{old_start} +{new_start} @@{body}")
            GitlabMcpClient._collect_line_numbers(
                body, old_start, new_start, added_lines, removed_lines
            )
        return hunks, added_lines, removed_lines

    @staticmethod
    def _collect_line_numbers(
        body: str,
        old_start: int,
        new_start: int,
        added_lines: list[int],
        removed_lines: list[int],
    ) -> None:
        """Walk diff body lines and record added/removed line numbers."""
        old_line, new_line = old_start, new_start
        for line in body.split("\n"):
            if line.startswith("+"):
                added_lines.append(new_line)
                new_line += 1
            elif line.startswith("-"):
                removed_lines.append(old_line)
                old_line += 1
            elif line.startswith(" ") or line == "":
                old_line += 1
                new_line += 1

    async def publish_review(self, mr_id: str, report: CodeReviewReport) -> None:
        status_label = "APPROVED" if report.is_approved else "CHANGES REQUESTED"
        main_note = f"### BrahMAS Code Review: {status_label}\n\n{report.summary}"

        await self._invoke_tool(
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
            await self._invoke_tool(
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
            await self._invoke_tool(
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

    async def execute_tool(self, tool_name: str, arguments: dict) -> Any:
        real_tool_name = tool_name.replace("vcs_", "gitlab_")
        if "project_id" not in arguments:
            arguments["project_id"] = self._project_id

        safe_args = self._redactor.sanitize(arguments)
        result = await self._invoke_tool(real_tool_name, safe_args)
        return self._extract_text(result)
