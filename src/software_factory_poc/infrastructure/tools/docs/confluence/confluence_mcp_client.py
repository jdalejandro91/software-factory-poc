import json
import logging
import os
from typing import Any

from mcp import McpError
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from software_factory_poc.core.application.tools import DocsTool
from software_factory_poc.core.application.tools.common.exceptions import ProviderError
from software_factory_poc.infrastructure.observability.redaction_service import RedactionService
from software_factory_poc.infrastructure.tools.docs.confluence.config.confluence_settings import (
    ConfluenceSettings,
)

logger = logging.getLogger(__name__)


class ConfluenceMcpClient(DocsTool):
    """MCP-stdio client that translates Domain intent into Confluence tool calls.

    Uses the shared Atlassian MCP server (covers both Jira and Confluence).
    """

    def __init__(self, settings: ConfluenceSettings) -> None:
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
        try:
            async with stdio_client(self._server_params()) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(tool_name, arguments=arguments)
        except McpError as exc:
            raise ProviderError(
                provider="ConfluenceMCP",
                message=f"MCP protocol error invoking '{tool_name}': {exc}",
                retryable=True,
            ) from exc
        except Exception as exc:
            raise ProviderError(
                provider="ConfluenceMCP",
                message=f"Connection failure invoking '{tool_name}': {exc}",
                retryable=True,
            ) from exc

        if result.isError:
            error_detail = self._extract_text(result) or "No detail"
            raise ProviderError(
                provider="ConfluenceMCP",
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

    # ── DocsTool implementation ──

    async def get_project_context(self, service_name: str) -> str:
        logger.info("[ConfluenceMCP] Fetching project context for '%s'", service_name)
        result = await self._invoke_tool(
            "confluence_search",
            {"query": service_name},
        )
        return self._extract_text(result)

    async def get_architecture_context(self, project_context_id: str) -> str:
        logger.info("[ConfluenceMCP] Fetching architecture page '%s'", project_context_id)
        result = await self._invoke_tool(
            "confluence_get_page",
            {"page_id": project_context_id},
        )
        raw = self._extract_text(result)
        try:
            data = json.loads(raw)
            return str(data.get("body", {}).get("storage", {}).get("value", raw))
        except (json.JSONDecodeError, TypeError):
            return raw

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
                    "name": t.name.replace("confluence_", "docs_"),
                    "description": t.description or "",
                    "parameters": t.inputSchema or {},
                },
            }
            for t in response.tools
            if t.name.startswith("confluence_")
        ]

    async def execute_tool(self, tool_name: str, arguments: dict[str, Any]) -> str:
        real_tool_name = tool_name.replace("docs_", "confluence_")
        safe_args = self._redactor.sanitize(arguments)
        result = await self._invoke_tool(real_tool_name, safe_args)
        return self._extract_text(result)
