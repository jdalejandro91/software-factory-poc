import contextlib
import json
import os
import re
from typing import Any

import structlog
from mcp import McpError
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from software_factory_poc.core.application.tools import DocsTool
from software_factory_poc.core.application.tools.common.exceptions import ProviderError
from software_factory_poc.infrastructure.observability.metrics_service import MCP_CALLS_TOTAL
from software_factory_poc.infrastructure.observability.redaction_service import RedactionService
from software_factory_poc.infrastructure.observability.tracing_setup import get_tracer
from software_factory_poc.infrastructure.tools.docs.confluence.config.confluence_settings import (
    ConfluenceSettings,
)

logger = structlog.get_logger()


class ConfluenceMcpClient(DocsTool):
    """MCP-stdio client that translates Domain intent into Confluence tool calls.

    Uses the shared Atlassian MCP server (covers both Jira and Confluence).
    """

    def __init__(self, settings: ConfluenceSettings) -> None:
        self._settings = settings
        self._redactor = RedactionService()
        self._exit_stack: contextlib.AsyncExitStack | None = None
        self._session: ClientSession | None = None

    # ── MCP lifecycle ──

    async def connect(self) -> None:
        """Open a persistent MCP session via AsyncExitStack."""
        if self._session is not None:
            return
        self._exit_stack = contextlib.AsyncExitStack()
        transport = await self._exit_stack.enter_async_context(stdio_client(self._server_params()))
        self._session = await self._exit_stack.enter_async_context(ClientSession(*transport))
        await self._session.initialize()
        logger.info("Persistent MCP session opened", source_system="ConfluenceMCP")

    async def disconnect(self) -> None:
        """Close the persistent MCP session and release subprocess resources."""
        if self._exit_stack is not None:
            await self._exit_stack.aclose()
            self._exit_stack = None
            self._session = None
            logger.info("Persistent MCP session closed", source_system="ConfluenceMCP")

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
            span.set_attribute("mcp.server", "ConfluenceMCP")
            span.set_attribute("mcp.tool_name", tool_name)
            logger.info("Invoking MCP tool", tool_name=tool_name, source_system="ConfluenceMCP")
            try:
                if self._session is not None:
                    result = await self._session.call_tool(tool_name, arguments=arguments)
                else:
                    async with stdio_client(self._server_params()) as (read, write):
                        async with ClientSession(read, write) as session:
                            await session.initialize()
                            result = await session.call_tool(tool_name, arguments=arguments)
            except McpError as exc:
                span.set_attribute("error", True)
                MCP_CALLS_TOTAL.labels(provider="confluence", tool=tool_name, outcome="error").inc()
                logger.error(
                    "MCP protocol error",
                    processing_status="ERROR",
                    error_type="McpError",
                    error_details=str(exc),
                    error_retryable=True,
                    source_system="ConfluenceMCP",
                    tags=["mcp-error"],
                )
                raise ProviderError(
                    provider="ConfluenceMCP",
                    message=f"MCP protocol error invoking '{tool_name}': {exc}",
                    retryable=True,
                ) from exc
            except Exception as exc:
                span.set_attribute("error", True)
                MCP_CALLS_TOTAL.labels(provider="confluence", tool=tool_name, outcome="error").inc()
                logger.error(
                    "MCP connection failure",
                    processing_status="ERROR",
                    error_type=type(exc).__name__,
                    error_details=str(exc),
                    error_retryable=True,
                    source_system="ConfluenceMCP",
                    tags=["mcp-error"],
                )
                raise ProviderError(
                    provider="ConfluenceMCP",
                    message=f"Connection failure invoking '{tool_name}': {exc}",
                    retryable=True,
                ) from exc

            if result.isError:
                error_detail = self._extract_text(result) or "No detail"
                span.set_attribute("error", True)
                MCP_CALLS_TOTAL.labels(provider="confluence", tool=tool_name, outcome="error").inc()
                logger.error(
                    "MCP tool returned error",
                    processing_status="ERROR",
                    error_type="McpToolError",
                    error_details=error_detail,
                    error_retryable=False,
                    source_system="ConfluenceMCP",
                    tags=["mcp-error"],
                )
                raise ProviderError(
                    provider="ConfluenceMCP",
                    message=f"Tool '{tool_name}' returned error: {error_detail}",
                    retryable=False,
                )

            MCP_CALLS_TOTAL.labels(provider="confluence", tool=tool_name, outcome="success").inc()
            logger.info("MCP tool completed", tool_name=tool_name, source_system="ConfluenceMCP")
            return result

    @staticmethod
    def _extract_text(result: Any) -> str:
        """Extract plain text from an MCP CallToolResult safely."""
        if result.content and len(result.content) > 0:
            first = result.content[0]
            return getattr(first, "text", str(first))
        return ""

    # ── DocsTool implementation ──

    async def get_architecture_context(self, page_id: str) -> str:
        """Fetch architecture standards page by explicit ID."""
        logger.info("Fetching architecture page", page_id=page_id, source_system="ConfluenceMCP")
        result = await self._invoke_tool("confluence_get_page", {"page_id": page_id})
        return self._clean_html_and_truncate(self._extract_text(result))

    async def get_project_context(self, service_name: str) -> str:
        """Hierarchical CQL search: find parent page by title, then fetch all children."""
        logger.info(
            "Fetching project context", service_name=service_name, source_system="ConfluenceMCP"
        )
        parent_id = await self._search_parent_page(service_name)
        if not parent_id:
            return f"No project documentation found for '{service_name}'."
        content = await self._fetch_children_content(parent_id)
        return self._clean_html_and_truncate(content)

    # ── Hierarchical Search Helpers ──

    async def _search_parent_page(self, service_name: str) -> str | None:
        """Search for the root page by title using CQL. Returns page ID or None."""
        cql = f'title="{service_name}"'
        result = await self._invoke_tool("confluence_search", {"cql": cql})
        raw = self._extract_text(result)
        return self._extract_first_page_id(raw)

    async def _fetch_children_content(self, parent_id: str) -> str:
        """Fetch all child pages under a parent and concatenate their content."""
        cql = f'ancestor="{parent_id}"'
        result = await self._invoke_tool("confluence_search", {"cql": cql})
        raw = self._extract_text(result)
        children = self._extract_page_list(raw)
        if not children:
            return f"Parent page {parent_id} has no child documents."
        sections: list[str] = []
        for child in children:
            content = await self._fetch_page_content(child["id"], child.get("title", "Untitled"))
            sections.append(content)
        return "\n\n".join(sections)

    async def _fetch_page_content(self, page_id: str, title: str) -> str:
        """Fetch a single page and format it as a titled section."""
        result = await self._invoke_tool("confluence_get_page", {"page_id": page_id})
        content = self._extract_text(result)
        return f"--- Document: {title} ---\n{content}"

    @staticmethod
    def _extract_first_page_id(raw: str) -> str | None:
        """Extract the ID of the first result from a CQL search response."""
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return None
        results = data.get("results", data) if isinstance(data, dict) else data
        if isinstance(results, list) and results:
            return str(results[0].get("id", ""))
        return None

    @staticmethod
    def _extract_page_list(raw: str) -> list[dict[str, str]]:
        """Extract a list of {id, title} dicts from a CQL search response."""
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return []
        results = data.get("results", data) if isinstance(data, dict) else data
        if not isinstance(results, list):
            return []
        return [
            {"id": str(r.get("id", "")), "title": str(r.get("title", "Untitled"))}
            for r in results
            if isinstance(r, dict) and r.get("id")
        ]

    @staticmethod
    def _clean_html_and_truncate(html_content: str, max_chars: int = 20000) -> str:
        """Strip HTML tags, normalize whitespace, and truncate to save LLM context tokens."""
        text = re.sub(r"<[^>]+>", " ", html_content)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{2,}", "\n", text).strip()
        if len(text) > max_chars:
            return text[:max_chars] + "... [CONTENIDO TRUNCADO POR LÍMITE DE CONTEXTO]"
        return text

    # ── Agentic Operations ──

    async def get_mcp_tools(self) -> list[dict[str, Any]]:
        """List available Confluence MCP tools for agentic mode."""
        try:
            if self._session is not None:
                response = await self._session.list_tools()
            else:
                async with stdio_client(self._server_params()) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        response = await session.list_tools()
        except McpError as exc:
            raise ProviderError(
                provider="ConfluenceMCP",
                message=f"Failed to list MCP tools: {exc}",
                retryable=True,
            ) from exc
        except Exception as exc:
            raise ProviderError(
                provider="ConfluenceMCP",
                message=f"Connection failure listing MCP tools: {exc}",
                retryable=True,
            ) from exc

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
        """Execute a single MCP tool call with argument sanitization."""
        real_tool_name = tool_name.replace("docs_", "confluence_")
        safe_args = self._redactor.sanitize(arguments)
        result = await self._invoke_tool(real_tool_name, safe_args)
        return self._extract_text(result)
