"""Abstract base for all MCP-stdio clients (GitLab, Jira, Confluence).

Centralises the shared lifecycle (connect / disconnect), tracing, metrics,
error handling, and ephemeral-session logic so that each concrete client
only needs to implement ``_server_params()``.
"""

import contextlib
from abc import ABC, abstractmethod
from typing import Any, NoReturn

import structlog
from mcp import McpError
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from software_factory_poc.core.application.tools.common.exceptions import ProviderError
from software_factory_poc.infrastructure.observability.metrics_service import MCP_CALLS_TOTAL
from software_factory_poc.infrastructure.observability.redaction_service import RedactionService
from software_factory_poc.infrastructure.observability.tracing_setup import get_tracer

logger = structlog.get_logger()


class BaseMcpClient(ABC):
    """Template base for MCP-stdio clients with shared lifecycle and error handling."""

    _PROVIDER: str = "BaseMCP"
    _METRICS_LABEL: str = "base"

    def __init__(self) -> None:
        self._redactor = RedactionService()
        self._exit_stack: contextlib.AsyncExitStack | None = None
        self._session: ClientSession | None = None

    # ── Abstract hook ──

    @abstractmethod
    def _server_params(self) -> StdioServerParameters:
        """Return provider-specific StdioServerParameters."""

    # ── MCP lifecycle ──

    async def connect(self) -> None:
        """Open a persistent MCP session via AsyncExitStack."""
        if self._session is not None:
            return
        self._exit_stack = contextlib.AsyncExitStack()
        transport = await self._exit_stack.enter_async_context(stdio_client(self._server_params()))
        self._session = await self._exit_stack.enter_async_context(ClientSession(*transport))
        await self._session.initialize()
        logger.info("Persistent MCP session opened", source_system=self._PROVIDER)

    async def disconnect(self) -> None:
        """Close the persistent MCP session and release subprocess resources."""
        if self._exit_stack is not None:
            try:
                await self._exit_stack.aclose()
            except Exception:  # noqa: BLE001
                logger.debug("Error closing MCP exit stack", source_system=self._PROVIDER)
            self._exit_stack = None
            self._session = None
            logger.info("Persistent MCP session closed", source_system=self._PROVIDER)

    # ── MCP call internals ──

    async def _invoke_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Invoke an MCP tool with tracing, metrics, and error translation."""
        tracer = get_tracer()
        with tracer.start_as_current_span("mcp.call_tool") as span:
            span.set_attribute("mcp.server", self._PROVIDER)
            span.set_attribute("mcp.tool_name", tool_name)
            logger.info("Invoking MCP tool", tool_name=tool_name, source_system=self._PROVIDER)
            result = await self._call_mcp_tool(tool_name, arguments, span)
            self._assert_no_tool_error(result, tool_name, span)
            MCP_CALLS_TOTAL.labels(
                provider=self._METRICS_LABEL, tool=tool_name, outcome="success"
            ).inc()
            logger.info("MCP tool completed", tool_name=tool_name, source_system=self._PROVIDER)
            return result

    async def _call_mcp_tool(self, tool_name: str, arguments: dict[str, Any], span: Any) -> Any:
        """Execute the MCP call via persistent or ephemeral session."""
        try:
            if self._session is not None:
                return await self._session.call_tool(tool_name, arguments=arguments)
            return await self._call_ephemeral(tool_name, arguments)
        except Exception as exc:
            self._raise_call_error(tool_name, span, exc)

    async def _call_ephemeral(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Open a one-shot stdio session, invoke the tool, and close."""
        async with stdio_client(self._server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                return await session.call_tool(tool_name, arguments=arguments)

    def _raise_call_error(self, tool_name: str, span: Any, exc: Exception) -> NoReturn:
        """Record metrics and raise ProviderError for MCP call failures."""
        is_protocol = isinstance(exc, McpError)
        label = "MCP protocol error" if is_protocol else "MCP connection failure"
        error_type = "McpError" if is_protocol else type(exc).__name__
        span.set_attribute("error", True)
        MCP_CALLS_TOTAL.labels(provider=self._METRICS_LABEL, tool=tool_name, outcome="error").inc()
        logger.error(
            label,
            processing_status="ERROR",
            error_type=error_type,
            error_details=str(exc),
            error_retryable=True,
            source_system=self._PROVIDER,
            tags=["mcp-error"],
        )
        raise ProviderError(
            provider=self._PROVIDER,
            message=f"{label} invoking '{tool_name}': {exc}",
            retryable=True,
        ) from exc

    def _assert_no_tool_error(self, result: Any, tool_name: str, span: Any) -> None:
        """Raise ProviderError if the MCP tool result indicates failure."""
        if not result.isError:
            return
        error_detail = self._extract_text(result) or "No detail"
        span.set_attribute("error", True)
        MCP_CALLS_TOTAL.labels(provider=self._METRICS_LABEL, tool=tool_name, outcome="error").inc()
        logger.error(
            "MCP tool returned error",
            processing_status="ERROR",
            error_type="McpToolError",
            error_details=error_detail,
            error_retryable=False,
            source_system=self._PROVIDER,
            tags=["mcp-error"],
        )
        raise ProviderError(
            provider=self._PROVIDER,
            message=f"Tool '{tool_name}' returned error: {error_detail}",
            retryable=False,
        )

    @staticmethod
    def _extract_text(result: Any) -> str:
        """Extract plain text from an MCP CallToolResult safely."""
        if result.content and len(result.content) > 0:
            first = result.content[0]
            return getattr(first, "text", str(first))
        return ""

    # ── Agentic tool listing ──

    async def _list_tools_response(self) -> Any:
        """Fetch the list of available MCP tools via persistent or ephemeral session."""
        try:
            if self._session is not None:
                return await self._session.list_tools()
            async with stdio_client(self._server_params()) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    return await session.list_tools()
        except Exception as exc:
            raise ProviderError(
                provider=self._PROVIDER,
                message=f"Failed to list MCP tools: {exc}",
                retryable=True,
            ) from exc
