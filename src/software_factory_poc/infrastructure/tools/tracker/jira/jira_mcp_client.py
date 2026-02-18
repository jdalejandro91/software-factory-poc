import json
import os
import re
from typing import Any

import structlog
import yaml
from mcp import McpError
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from software_factory_poc.core.application.tools import TrackerTool
from software_factory_poc.core.application.tools.common.exceptions import ProviderError
from software_factory_poc.core.domain.mission import Mission, TaskDescription
from software_factory_poc.core.domain.quality import CodeReviewReport
from software_factory_poc.infrastructure.observability.metrics_service import MCP_CALLS_TOTAL
from software_factory_poc.infrastructure.observability.redaction_service import RedactionService
from software_factory_poc.infrastructure.observability.tracing_setup import get_tracer
from software_factory_poc.infrastructure.tools.tracker.jira.config.jira_settings import (
    JiraSettings,
)

logger = structlog.get_logger()

_CONFIG_BLOCK_RE = re.compile(
    r"```(?:scaffolder|yaml|yml)\s*([\s\S]*?)\s*```",
    re.IGNORECASE,
)


class JiraMcpClient(TrackerTool):
    """MCP-stdio client that translates Domain intent into Jira tool calls.

    Uses the shared Atlassian MCP server (covers both Jira and Confluence).
    """

    def __init__(self, settings: JiraSettings) -> None:
        self._settings = settings
        self._redactor = RedactionService()

    # ── MCP connection internals ──

    def _server_params(self) -> StdioServerParameters:
        """Build StdioServerParameters with Atlassian credentials injected into subprocess env."""
        env = os.environ.copy()
        if self._settings.api_token:
            env["ATLASSIAN_API_TOKEN"] = self._settings.api_token.get_secret_value()
        env["ATLASSIAN_USER_EMAIL"] = self._settings.user_email
        env["ATLASSIAN_HOST"] = self._settings.base_url
        return StdioServerParameters(
            command=self._settings.mcp_atlassian_command,
            args=self._settings.mcp_atlassian_args,
            env=env,
        )

    async def _invoke_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Open an stdio MCP session, invoke the tool, and translate errors."""
        tracer = get_tracer()
        with tracer.start_as_current_span("mcp.call_tool") as span:
            span.set_attribute("mcp.server", "JiraMCP")
            span.set_attribute("mcp.tool_name", tool_name)
            logger.info("Invoking MCP tool", tool_name=tool_name, source_system="JiraMCP")
            try:
                async with stdio_client(self._server_params()) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        result = await session.call_tool(tool_name, arguments=arguments)
            except McpError as exc:
                span.set_attribute("error", True)
                MCP_CALLS_TOTAL.labels(provider="jira", tool=tool_name, outcome="error").inc()
                logger.error(
                    "MCP protocol error",
                    processing_status="ERROR",
                    error_type="McpError",
                    error_details=str(exc),
                    error_retryable=True,
                    source_system="JiraMCP",
                    tags=["mcp-error"],
                )
                raise ProviderError(
                    provider="JiraMCP",
                    message=f"MCP protocol error invoking '{tool_name}': {exc}",
                    retryable=True,
                ) from exc
            except Exception as exc:
                span.set_attribute("error", True)
                MCP_CALLS_TOTAL.labels(provider="jira", tool=tool_name, outcome="error").inc()
                logger.error(
                    "MCP connection failure",
                    processing_status="ERROR",
                    error_type=type(exc).__name__,
                    error_details=str(exc),
                    error_retryable=True,
                    source_system="JiraMCP",
                    tags=["mcp-error"],
                )
                raise ProviderError(
                    provider="JiraMCP",
                    message=f"Connection failure invoking '{tool_name}': {exc}",
                    retryable=True,
                ) from exc

            if result.isError:
                error_detail = self._extract_text(result) or "No detail"
                span.set_attribute("error", True)
                MCP_CALLS_TOTAL.labels(provider="jira", tool=tool_name, outcome="error").inc()
                logger.error(
                    "MCP tool returned error",
                    processing_status="ERROR",
                    error_type="McpToolError",
                    error_details=error_detail,
                    error_retryable=False,
                    source_system="JiraMCP",
                    tags=["mcp-error"],
                )
                raise ProviderError(
                    provider="JiraMCP",
                    message=f"Tool '{tool_name}' returned error: {error_detail}",
                    retryable=False,
                )

            MCP_CALLS_TOTAL.labels(provider="jira", tool=tool_name, outcome="success").inc()
            logger.info("MCP tool completed", tool_name=tool_name, source_system="JiraMCP")
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

    # ── TrackerTool implementation ──

    async def get_task(self, ticket_id: str) -> Mission:
        logger.info("Fetching task", ticket_id=ticket_id, source_system="JiraMCP")
        result = await self._invoke_tool("jira_get_issue", {"issue_key": ticket_id})
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
        logger.info("Adding comment", ticket_id=ticket_id, source_system="JiraMCP")
        await self._invoke_tool(
            "jira_add_comment",
            {"issue_key": ticket_id, "comment": comment},
        )

    async def update_status(self, ticket_id: str, status: str) -> None:
        logger.info(
            "Transitioning status",
            ticket_id=ticket_id,
            target_status=status,
            source_system="JiraMCP",
        )
        await self._invoke_tool(
            "jira_transition_issue",
            {"issue_key": ticket_id, "transition_name": status},
        )

    async def update_task_description(self, ticket_id: str, appended_text: str) -> None:
        """Fetch current description and append new text (get-then-update via MCP)."""
        logger.info("Appending to description", ticket_id=ticket_id, source_system="JiraMCP")
        current = await self._fetch_current_description(ticket_id)
        updated = current + appended_text
        await self._invoke_tool(
            "jira_update_issue",
            {"issue_key": ticket_id, "fields": {"description": updated}},
        )

    async def _fetch_current_description(self, ticket_id: str) -> str:
        """Retrieve the current Jira issue description via MCP."""
        result = await self._invoke_tool("jira_get_issue", {"issue_key": ticket_id})
        data = self._parse_json(
            self._extract_text(result), context=f"fetch_description({ticket_id})"
        )
        return data.get("fields", {}).get("description", "") or ""

    async def post_review_summary(self, ticket_id: str, report: CodeReviewReport) -> None:
        logger.info("Posting review summary", ticket_id=ticket_id, source_system="JiraMCP")
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
        await self._invoke_tool(
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
                "type": "function",
                "function": {
                    "name": t.name.replace("jira_", "tracker_"),
                    "description": t.description or "",
                    "parameters": t.inputSchema or {},
                },
            }
            for t in response.tools
            if t.name.startswith("jira_")
        ]

    async def execute_tool(self, tool_name: str, arguments: dict) -> Any:
        real_tool_name = tool_name.replace("tracker_", "jira_")
        safe_args = self._redactor.sanitize(arguments)
        result = await self._invoke_tool(real_tool_name, safe_args)
        return self._extract_text(result)
