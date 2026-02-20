"""MCP-stdio client that translates Domain intent into Jira tool calls.

Uses the shared Atlassian MCP server (covers both Jira and Confluence).
"""

import json
import os
from typing import Any

import structlog
from mcp.client.stdio import StdioServerParameters

from software_factory_poc.core.application.tools import TrackerTool
from software_factory_poc.core.application.tools.common.exceptions import ProviderError
from software_factory_poc.infrastructure.tools.common.base_mcp_client import BaseMcpClient
from software_factory_poc.infrastructure.tools.tracker.jira.config.jira_settings import (
    JiraSettings,
)
from software_factory_poc.infrastructure.tools.tracker.jira.jira_description_builder import (
    build_updated_description,
)

logger = structlog.get_logger()


class JiraMcpClient(BaseMcpClient, TrackerTool):
    """Thin MCP client: inherits lifecycle from BaseMcpClient, delegates parsing to helpers."""

    _PROVIDER: str = "JiraMCP"
    _METRICS_LABEL: str = "jira"

    def __init__(self, settings: JiraSettings) -> None:
        super().__init__()
        self._settings = settings

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

    # ── TrackerTool implementation ──

    async def add_comment(self, ticket_id: str, comment: str) -> None:
        logger.info("Adding comment", ticket_id=ticket_id, source_system="JiraMCP")
        await self._invoke_tool(
            "jira_add_comment",
            {"issue_key": ticket_id, "comment": comment},
        )

    async def update_status(self, ticket_id: str, status: str) -> None:
        logger.info("Transitioning status", ticket_id=ticket_id, source_system="JiraMCP")
        transition_id = await self._resolve_transition_id(ticket_id, status)
        await self._invoke_tool(
            "jira_transition_issue",
            {"issue_key": ticket_id, "transition_id": transition_id},
        )

    async def update_task_description(self, ticket_id: str, appended_text: str) -> None:
        logger.info("Appending to description", ticket_id=ticket_id, source_system="JiraMCP")
        current = await self._fetch_current_description(ticket_id)
        updated = build_updated_description(current, appended_text)
        await self._invoke_tool(
            "jira_update_issue",
            {"issue_key": ticket_id, "fields": {"description": updated}},
        )

    # ── Agentic Operations ──

    async def get_mcp_tools(self) -> list[dict[str, Any]]:
        response = await self._list_tools_response()
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

    async def execute_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        real_tool_name = tool_name.replace("tracker_", "jira_")
        safe_args = self._redactor.sanitize(arguments)
        result = await self._invoke_tool(real_tool_name, safe_args)
        return self._extract_text(result)

    # ── Private helpers ──

    def _parse_json(self, raw_text: str, context: str) -> dict[str, Any]:
        """Parse JSON from MCP response with clean error handling."""
        try:
            return dict(json.loads(raw_text))
        except (json.JSONDecodeError, TypeError) as exc:
            raise ProviderError(
                provider="JiraMCP",
                message=f"Non-JSON response in '{context}': {raw_text[:200]}",
            ) from exc

    async def _resolve_transition_id(self, ticket_id: str, target_status: str) -> str:
        result = await self._invoke_tool("jira_get_transitions", {"issue_key": ticket_id})
        transitions_json = self._parse_json(
            self._extract_text(result), context=f"get_transitions({ticket_id})"
        )
        target_lower = target_status.lower()
        for t in transitions_json.get("transitions", []):
            name = (t.get("name") or "").lower()
            to_name = ((t.get("to") or {}).get("name") or "").lower()
            if target_lower in (name, to_name):
                return str(t["id"])
        raise ProviderError(
            provider="JiraMCP",
            message=f"Transition not found for status '{target_status}' on issue {ticket_id}.",
        )

    async def _fetch_current_description(self, ticket_id: str) -> str | dict[str, Any] | None:
        result = await self._invoke_tool("jira_get_issue", {"issue_key": ticket_id})
        issue_json = self._parse_json(
            self._extract_text(result), context=f"fetch_description({ticket_id})"
        )
        return (issue_json.get("fields") or {}).get("description")
