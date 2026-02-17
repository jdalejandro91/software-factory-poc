"""Unit tests — ConfluenceMcpClient (zero I/O, fully mocked MCP stdio)."""

import json
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from mcp import McpError
from mcp.types import ErrorData
from pydantic import SecretStr

from software_factory_poc.core.application.ports import DocsPort
from software_factory_poc.core.application.ports.common.exceptions import ProviderError
from software_factory_poc.infrastructure.tools.docs.confluence.config.confluence_settings import (
    ConfluenceSettings,
)
from software_factory_poc.infrastructure.tools.docs.confluence.confluence_mcp_client import (
    ConfluenceMcpClient,
)

MODULE = "software_factory_poc.infrastructure.tools.docs.confluence.confluence_mcp_client"


# ── Fakes for MCP response structures ──


@dataclass
class FakeTextContent:
    text: str


@dataclass
class FakeCallToolResult:
    content: list[Any] = field(default_factory=list)
    isError: bool = False
    structuredContent: dict[str, Any] | None = None
    meta: dict[str, Any] | None = None


@dataclass
class FakeTool:
    name: str
    description: str = "A tool"
    inputSchema: dict[str, Any] = field(default_factory=dict)


@dataclass
class FakeListToolsResult:
    tools: list[FakeTool] = field(default_factory=list)


# ── Helpers ──


def _make_settings(**overrides: Any) -> ConfluenceSettings:
    defaults: dict[str, Any] = {
        "CONFLUENCE_API_TOKEN": SecretStr("atlassian-token-123"),
        "CONFLUENCE_USER_EMAIL": "bot@company.io",
        "CONFLUENCE_BASE_URL": "https://company.atlassian.net",
        "ARCHITECTURE_DOC_PAGE_ID": "9999",
        "MCP_ATLASSIAN_COMMAND": "npx",
        "MCP_ATLASSIAN_ARGS": ["@anthropic/mcp-server-atlassian"],
    }
    defaults.update(overrides)
    return ConfluenceSettings(**defaults)


def _build_client(settings: ConfluenceSettings | None = None) -> ConfluenceMcpClient:
    return ConfluenceMcpClient(settings=settings or _make_settings())


def _text_result(text: str) -> FakeCallToolResult:
    return FakeCallToolResult(content=[FakeTextContent(text=text)])


def _error_result(text: str) -> FakeCallToolResult:
    return FakeCallToolResult(content=[FakeTextContent(text=text)], isError=True)


# ── Fixture: mock the entire MCP stdio stack ──


@pytest.fixture
def mock_mcp():
    """Patch stdio_client + ClientSession to intercept all MCP calls without I/O."""
    mock_session = AsyncMock()
    mock_session.initialize = AsyncMock()
    mock_session.call_tool = AsyncMock()
    mock_session.list_tools = AsyncMock()

    @asynccontextmanager
    async def fake_stdio_client(_params: Any):
        yield (AsyncMock(), AsyncMock())

    @asynccontextmanager
    async def fake_client_session(_read: Any, _write: Any):
        yield mock_session

    with (
        patch(f"{MODULE}.stdio_client", side_effect=fake_stdio_client),
        patch(f"{MODULE}.ClientSession", side_effect=fake_client_session),
    ):
        yield mock_session


# ══════════════════════════════════════════════════════════════════════
# Port compliance
# ══════════════════════════════════════════════════════════════════════


class TestPortCompliance:
    def test_implements_docs_port(self) -> None:
        client = _build_client()
        assert isinstance(client, DocsPort)
        assert isinstance(client, ConfluenceMcpClient)


# ══════════════════════════════════════════════════════════════════════
# _server_params — Atlassian credential injection
# ══════════════════════════════════════════════════════════════════════


class TestServerParams:
    def test_injects_atlassian_env_vars(self) -> None:
        client = _build_client()
        params = client._server_params()

        assert params.command == "npx"
        assert params.args == ["@anthropic/mcp-server-atlassian"]
        assert params.env is not None
        assert params.env["ATLASSIAN_API_TOKEN"] == "atlassian-token-123"
        assert params.env["ATLASSIAN_USER_EMAIL"] == "bot@company.io"
        assert params.env["ATLASSIAN_HOST"] == "https://company.atlassian.net"

    def test_env_is_copy_of_os_environ(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SENTINEL_VAR", "present")
        client = _build_client()
        params = client._server_params()

        assert params.env is not None
        assert params.env["SENTINEL_VAR"] == "present"

    def test_skips_token_when_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("CONFLUENCE_API_TOKEN", raising=False)
        settings = ConfluenceSettings(
            CONFLUENCE_BASE_URL="https://test.atlassian.net",
            CONFLUENCE_USER_EMAIL="user@test.io",
            MCP_ATLASSIAN_ARGS=["server"],
            _env_file=None,  # type: ignore[call-arg]
        )
        client = _build_client(settings)
        params = client._server_params()

        assert params.env is not None
        assert "ATLASSIAN_API_TOKEN" not in params.env


# ══════════════════════════════════════════════════════════════════════
# get_project_context
# ══════════════════════════════════════════════════════════════════════


class TestGetProjectContext:
    async def test_searches_confluence_and_returns_text(self, mock_mcp: AsyncMock) -> None:
        mock_mcp.call_tool.return_value = _text_result("BrahMAS architecture overview...")
        client = _build_client()

        result = await client.get_project_context("BrahMAS")

        assert result == "BrahMAS architecture overview..."
        mock_mcp.call_tool.assert_called_once_with(
            "confluence_search",
            arguments={"query": "BrahMAS"},
        )

    async def test_returns_empty_on_no_content(self, mock_mcp: AsyncMock) -> None:
        mock_mcp.call_tool.return_value = FakeCallToolResult(content=[])
        client = _build_client()

        result = await client.get_project_context("unknown-service")
        assert result == ""


# ══════════════════════════════════════════════════════════════════════
# get_architecture_context
# ══════════════════════════════════════════════════════════════════════


class TestGetArchitectureContext:
    async def test_fetches_page_and_extracts_body(self, mock_mcp: AsyncMock) -> None:
        page_data = {"body": {"storage": {"value": "<h1>Clean Architecture</h1>"}}}
        mock_mcp.call_tool.return_value = _text_result(json.dumps(page_data))
        client = _build_client()

        result = await client.get_architecture_context("3571713")

        assert result == "<h1>Clean Architecture</h1>"
        mock_mcp.call_tool.assert_called_once_with(
            "confluence_get_page",
            arguments={"page_id": "3571713"},
        )

    async def test_returns_raw_text_on_non_json(self, mock_mcp: AsyncMock) -> None:
        mock_mcp.call_tool.return_value = _text_result("Plain text page content")
        client = _build_client()

        result = await client.get_architecture_context("1234")
        assert result == "Plain text page content"

    async def test_returns_raw_when_body_key_missing(self, mock_mcp: AsyncMock) -> None:
        mock_mcp.call_tool.return_value = _text_result(json.dumps({"title": "My Page"}))
        client = _build_client()

        result = await client.get_architecture_context("5678")
        assert result == json.dumps({"title": "My Page"})


# ══════════════════════════════════════════════════════════════════════
# Error handling
# ══════════════════════════════════════════════════════════════════════


class TestErrorHandling:
    async def test_mcp_error_becomes_provider_error(self, mock_mcp: AsyncMock) -> None:
        mock_mcp.call_tool.side_effect = McpError(ErrorData(code=-32600, message="Invalid request"))
        client = _build_client()

        with pytest.raises(ProviderError, match="MCP protocol error"):
            await client.get_project_context("fail-service")

    async def test_connection_failure_becomes_provider_error(self, mock_mcp: AsyncMock) -> None:
        mock_mcp.call_tool.side_effect = ConnectionError("stdio pipe broken")
        client = _build_client()

        with pytest.raises(ProviderError, match="Connection failure"):
            await client.get_architecture_context("broken-page")

    async def test_tool_is_error_becomes_provider_error(self, mock_mcp: AsyncMock) -> None:
        mock_mcp.call_tool.return_value = _error_result("Page not found")
        client = _build_client()

        with pytest.raises(ProviderError, match="Tool .* returned error"):
            await client.get_architecture_context("404")

    async def test_provider_error_includes_provider_name(self, mock_mcp: AsyncMock) -> None:
        mock_mcp.call_tool.side_effect = RuntimeError("boom")
        client = _build_client()

        with pytest.raises(ProviderError) as exc_info:
            await client.get_project_context("crash")

        assert exc_info.value.provider == "ConfluenceMCP"
        assert exc_info.value.retryable is True


# ══════════════════════════════════════════════════════════════════════
# Agentic operations — get_mcp_tools
# ══════════════════════════════════════════════════════════════════════


class TestGetMcpTools:
    async def test_filters_and_renames_confluence_tools(self, mock_mcp: AsyncMock) -> None:
        mock_mcp.list_tools.return_value = FakeListToolsResult(
            tools=[
                FakeTool(name="confluence_search", description="Searches Confluence"),
                FakeTool(name="confluence_get_page", description="Gets a page"),
                FakeTool(name="jira_get_issue", description="Not confluence"),
            ]
        )
        client = _build_client()

        tools = await client.get_mcp_tools()

        assert len(tools) == 2
        assert tools[0]["type"] == "function"
        assert tools[0]["function"]["name"] == "docs_search"
        assert tools[0]["function"]["description"] == "Searches Confluence"
        assert tools[1]["function"]["name"] == "docs_get_page"

    async def test_excludes_non_confluence_tools(self, mock_mcp: AsyncMock) -> None:
        mock_mcp.list_tools.return_value = FakeListToolsResult(
            tools=[
                FakeTool(name="jira_get_issue"),
                FakeTool(name="gitlab_create_branch"),
            ]
        )
        client = _build_client()

        tools = await client.get_mcp_tools()
        assert tools == []


# ══════════════════════════════════════════════════════════════════════
# Agentic operations — execute_tool
# ══════════════════════════════════════════════════════════════════════


class TestExecuteTool:
    async def test_translates_docs_prefix_to_confluence(self, mock_mcp: AsyncMock) -> None:
        mock_mcp.call_tool.return_value = _text_result("result-data")
        client = _build_client()

        result = await client.execute_tool("docs_search", {"query": "BrahMAS"})

        assert result == "result-data"
        call_args = mock_mcp.call_tool.call_args
        assert call_args[0][0] == "confluence_search"

    async def test_sanitizes_arguments_via_redactor(self, mock_mcp: AsyncMock) -> None:
        mock_mcp.call_tool.return_value = _text_result("ok")
        client = _build_client()

        await client.execute_tool("docs_get_page", {"page_id": "123"})

        call_args = mock_mcp.call_tool.call_args
        payload = call_args[1]["arguments"]
        assert "page_id" in payload
