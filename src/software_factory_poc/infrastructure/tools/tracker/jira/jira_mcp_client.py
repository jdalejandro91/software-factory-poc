import json
import logging
import os
import re
from typing import Any

import yaml
from mcp import McpError
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from software_factory_poc.core.application.ports.common.exceptions.provider_error import (
    ProviderError,
)
from software_factory_poc.core.application.ports.tracker_port import TrackerPort
from software_factory_poc.core.domain.mission.entities.mission import Mission
from software_factory_poc.core.domain.mission.value_objects.task_description import TaskDescription
from software_factory_poc.core.domain.quality.code_review_report import CodeReviewReport
from software_factory_poc.infrastructure.observability.redaction_service import RedactionService
from software_factory_poc.infrastructure.tools.tracker.jira.config.jira_settings import (
    JiraSettings,
)

logger = logging.getLogger(__name__)

_CONFIG_BLOCK_RE = re.compile(
    r"```(?:scaffolder|yaml|yml)\s*([\s\S]*?)\s*```",
    re.IGNORECASE,
)


class JiraMcpClient(TrackerPort):
    """MCP-stdio client that translates Domain intent into Jira tool calls.

    Uses the shared Atlassian MCP server (covers both Jira and Confluence).
    """

    def __init__(self, settings: JiraSettings, redactor: RedactionService) -> None:
        self._settings = settings
        self._redactor = redactor

    # ── MCP connection internals ──

    def _server_params(self) -> StdioServerParameters:
        """Build StdioServerParameters with Atlassian credentials injected into subprocess env."""
        env = {**os.environ}
        if self._settings.api_token:
            env["ATLASSIAN_API_TOKEN"] = self._settings.api_token.get_secret_value()
        env["ATLASSIAN_USER_EMAIL"] = self._settings.user_email
        env["ATLASSIAN_HOST"] = self._settings.base_url
        return StdioServerParameters(
            command=self._settings.mcp_atlassian_command,
            args=self._settings.mcp_atlassian_args,
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
                provider="JiraMCP",
                message=f"MCP protocol error invoking '{tool_name}': {exc}",
                retryable=True,
            ) from exc
        except Exception as exc:
            raise ProviderError(
                provider="JiraMCP",
                message=f"Connection failure invoking '{tool_name}': {exc}",
                retryable=True,
            ) from exc

        if result.isError:
            error_detail = self._extract_text(result) or "No detail"
            raise ProviderError(
                provider="JiraMCP",
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

    def _parse_json(self, raw_text: str, context: str) -> dict[str, Any]:
        """Parse JSON from MCP response with clean error handling."""
        try:
            return json.loads(raw_text)
        except (json.JSONDecodeError, TypeError) as exc:
            raise ProviderError(
                provider="JiraMCP",
                message=f"Non-JSON response in '{context}': {raw_text[:200]}",
            ) from exc

    @staticmethod
    def _parse_description(text: str) -> TaskDescription:
        """Parse Markdown description into TaskDescription, extracting YAML config blocks."""
        if not text:
            return TaskDescription(raw_content="", config={})

        config: dict[str, Any] = {}
        match = _CONFIG_BLOCK_RE.search(text)
        if match:
            try:
                parsed = yaml.safe_load(match.group(1).strip())
                if isinstance(parsed, dict):
                    config = parsed
            except yaml.YAMLError:
                pass
            raw_content = text.replace(match.group(0), "").strip()
        else:
            raw_content = text

        return TaskDescription(raw_content=raw_content, config=config)

    # ── TrackerPort implementation ──

    async def get_task(self, ticket_id: str) -> Mission:
        logger.info("[JiraMCP] Fetching task %s", ticket_id)
        result = await self._call_mcp("jira_get_issue", {"issue_key": ticket_id})
        data = self._parse_json(self._extract_text(result), context=f"get_task({ticket_id})")

        fields = data.get("fields", {})
        description_text = fields.get("description", "") or ""
        task_description = self._parse_description(description_text)

        return Mission(
            id=data.get("id", ticket_id),
            key=data.get("key", ticket_id),
            summary=fields.get("summary", ""),
            status=fields.get("status", {}).get("name", "OPEN"),
            project_key=fields.get("project", {}).get("key", ""),
            issue_type=fields.get("issuetype", {}).get("name", "Task"),
            description=task_description,
        )

    async def add_comment(self, ticket_id: str, comment: str) -> None:
        logger.info("[JiraMCP] Adding comment to %s", ticket_id)
        await self._call_mcp(
            "jira_add_comment",
            {"issue_key": ticket_id, "comment": comment},
        )

    async def update_status(self, ticket_id: str, status: str) -> None:
        logger.info("[JiraMCP] Transitioning %s → '%s'", ticket_id, status)
        await self._call_mcp(
            "jira_transition_issue",
            {"issue_key": ticket_id, "transition_name": status},
        )

    async def update_task_description(self, ticket_id: str, description: str) -> None:
        logger.info("[JiraMCP] Updating description of %s", ticket_id)
        await self._call_mcp(
            "jira_update_issue",
            {"issue_key": ticket_id, "fields": {"description": description}},
        )

    async def post_review_summary(self, ticket_id: str, report: CodeReviewReport) -> None:
        logger.info("[JiraMCP] Posting review summary to %s", ticket_id)
        status_label = "APPROVED" if report.is_approved else "CHANGES REQUESTED"

        lines = [f"## BrahMAS Code Review: {status_label}", "", report.summary]

        if report.comments:
            lines += ["", "### Findings", "", "| Severity | File | Description |"]
            lines.append("|----------|------|-------------|")
            for issue in report.comments:
                line_ref = f":{issue.line_number}" if issue.line_number else ""
                lines.append(
                    f"| **{issue.severity.value}** "
                    f"| `{issue.file_path}{line_ref}` "
                    f"| {issue.description} |"
                )

        comment_md = "\n".join(lines)

        transition = (
            self._settings.workflow_state_success
            if report.is_approved
            else self._settings.workflow_state_initial
        )
        await self.update_status(ticket_id, transition)
        await self._call_mcp(
            "jira_add_comment",
            {"issue_key": ticket_id, "comment": comment_md},
        )

    # ── Agentic Operations ──

    async def get_mcp_tools(self) -> list[dict[str, Any]]:
        async with stdio_client(self._server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                response = await session.list_tools()

        return [
            {
                "name": t.name.replace("jira_", "tracker_"),
                "description": t.description,
                "inputSchema": t.inputSchema,
            }
            for t in response.tools
            if t.name.startswith("jira_")
        ]

    async def execute_tool(self, tool_name: str, arguments: dict) -> Any:
        real_tool_name = tool_name.replace("tracker_", "jira_")
        safe_args = self._redactor.sanitize(arguments)
        result = await self._call_mcp(real_tool_name, safe_args)
        return self._extract_text(result)
