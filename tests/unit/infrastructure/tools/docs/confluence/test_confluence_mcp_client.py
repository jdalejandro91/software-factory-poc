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

from software_factory_poc.core.application.tools import DocsTool
from software_factory_poc.core.application.tools.common.exceptions import ProviderError
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


def _search_result(results: list[dict[str, Any]]) -> FakeCallToolResult:
    return _text_result(json.dumps({"results": results}))


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
        assert isinstance(client, DocsTool)
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
# get_architecture_context
# ══════════════════════════════════════════════════════════════════════


class TestGetArchitectureContext:
    async def test_fetches_page_and_strips_html(self, mock_mcp: AsyncMock) -> None:
        mock_mcp.call_tool.return_value = _text_result("<h1>Clean Architecture</h1>")
        client = _build_client()

        result = await client.get_architecture_context("3571713")

        assert result == "Clean Architecture"
        mock_mcp.call_tool.assert_called_once_with(
            "confluence_get_page",
            arguments={"page_id": "3571713"},
        )

    async def test_returns_empty_on_no_content(self, mock_mcp: AsyncMock) -> None:
        mock_mcp.call_tool.return_value = FakeCallToolResult(content=[])
        client = _build_client()

        result = await client.get_architecture_context("1234")
        assert result == ""


# ══════════════════════════════════════════════════════════════════════
# get_project_context — hierarchical CQL search
# ══════════════════════════════════════════════════════════════════════


class TestGetProjectContext:
    async def test_happy_path_fetches_parent_then_children(self, mock_mcp: AsyncMock) -> None:
        """Full flow: find parent by title → find children → fetch each child page."""
        parent_search = _search_result([{"id": "100", "title": "shopping-cart"}])
        children_search = _search_result(
            [
                {"id": "201", "title": "HLD"},
                {"id": "202", "title": "ADR-001"},
            ]
        )
        child_page_1 = _text_result("<p>High Level Design content</p>")
        child_page_2 = _text_result("<p>ADR decision record</p>")

        mock_mcp.call_tool.side_effect = [
            parent_search,
            children_search,
            child_page_1,
            child_page_2,
        ]
        client = _build_client()

        result = await client.get_project_context("shopping-cart")

        assert "--- Document: HLD ---" in result
        assert "High Level Design content" in result
        assert "--- Document: ADR-001 ---" in result
        assert "ADR decision record" in result
        assert "<p>" not in result

        calls = mock_mcp.call_tool.call_args_list
        assert calls[0][0][0] == "confluence_search"
        assert calls[0][1]["arguments"]["cql"] == 'title="shopping-cart"'
        assert calls[1][0][0] == "confluence_search"
        assert calls[1][1]["arguments"]["cql"] == 'ancestor="100"'
        assert calls[2][0][0] == "confluence_get_page"
        assert calls[3][0][0] == "confluence_get_page"

    async def test_returns_fallback_when_no_parent_found(self, mock_mcp: AsyncMock) -> None:
        mock_mcp.call_tool.return_value = _search_result([])
        client = _build_client()

        result = await client.get_project_context("unknown-service")

        assert "No project documentation found" in result
        assert "unknown-service" in result

    async def test_returns_fallback_when_parent_has_no_children(self, mock_mcp: AsyncMock) -> None:
        parent_search = _search_result([{"id": "100", "title": "empty-project"}])
        children_search = _search_result([])

        mock_mcp.call_tool.side_effect = [parent_search, children_search]
        client = _build_client()

        result = await client.get_project_context("empty-project")

        assert "no child documents" in result

    async def test_returns_fallback_on_non_json_search_result(self, mock_mcp: AsyncMock) -> None:
        mock_mcp.call_tool.return_value = _text_result("not valid json")
        client = _build_client()

        result = await client.get_project_context("bad-format")

        assert "No project documentation found" in result


# ══════════════════════════════════════════════════════════════════════
# Static helper methods
# ══════════════════════════════════════════════════════════════════════


class TestExtractFirstPageId:
    def test_extracts_id_from_results_list(self) -> None:
        raw = json.dumps({"results": [{"id": "42", "title": "Page"}]})
        assert ConfluenceMcpClient._extract_first_page_id(raw) == "42"

    def test_returns_none_on_empty_results(self) -> None:
        raw = json.dumps({"results": []})
        assert ConfluenceMcpClient._extract_first_page_id(raw) is None

    def test_returns_none_on_invalid_json(self) -> None:
        assert ConfluenceMcpClient._extract_first_page_id("not json") is None

    def test_handles_flat_list_format(self) -> None:
        raw = json.dumps([{"id": "99", "title": "Flat"}])
        assert ConfluenceMcpClient._extract_first_page_id(raw) == "99"


class TestExtractPageList:
    def test_extracts_list_of_dicts(self) -> None:
        raw = json.dumps(
            {
                "results": [
                    {"id": "1", "title": "A"},
                    {"id": "2", "title": "B"},
                ]
            }
        )
        pages = ConfluenceMcpClient._extract_page_list(raw)
        assert len(pages) == 2
        assert pages[0] == {"id": "1", "title": "A"}

    def test_returns_empty_on_invalid_json(self) -> None:
        assert ConfluenceMcpClient._extract_page_list("not json") == []

    def test_skips_entries_without_id(self) -> None:
        raw = json.dumps({"results": [{"title": "No ID"}, {"id": "5", "title": "Has ID"}]})
        pages = ConfluenceMcpClient._extract_page_list(raw)
        assert len(pages) == 1
        assert pages[0]["id"] == "5"


# ══════════════════════════════════════════════════════════════════════
# _clean_html_and_truncate — HTML stripping + context pruning
# ══════════════════════════════════════════════════════════════════════


class TestCleanHtmlAndTruncate:
    def test_strips_html_tags(self) -> None:
        result = ConfluenceMcpClient._clean_html_and_truncate("<h1>Title</h1><p>Body text</p>")
        assert "<h1>" not in result
        assert "<p>" not in result
        assert "Title" in result
        assert "Body text" in result

    def test_normalizes_whitespace(self) -> None:
        result = ConfluenceMcpClient._clean_html_and_truncate("word1   word2\t\tword3")
        assert result == "word1 word2 word3"

    def test_collapses_multiple_newlines(self) -> None:
        result = ConfluenceMcpClient._clean_html_and_truncate("line1\n\n\n\nline2")
        assert result == "line1\nline2"

    def test_truncates_at_max_chars(self) -> None:
        long_text = "A" * 25000
        result = ConfluenceMcpClient._clean_html_and_truncate(long_text, max_chars=100)
        assert len(result) > 100  # includes suffix
        assert result.startswith("A" * 100)
        assert "CONTENIDO TRUNCADO" in result

    def test_does_not_truncate_within_limit(self) -> None:
        text = "Short content"
        result = ConfluenceMcpClient._clean_html_and_truncate(text, max_chars=20000)
        assert result == text
        assert "TRUNCADO" not in result

    def test_handles_empty_string(self) -> None:
        assert ConfluenceMcpClient._clean_html_and_truncate("") == ""

    def test_complex_confluence_html(self) -> None:
        html = (
            '<ac:structured-macro ac:name="toc"/>'
            "<h2>Overview</h2>"
            '<div class="panel"><p>Architecture <strong>rules</strong>:</p></div>'
            "<ul><li>Rule 1</li><li>Rule 2</li></ul>"
        )
        result = ConfluenceMcpClient._clean_html_and_truncate(html)
        assert "Overview" in result
        assert "Architecture" in result
        assert "rules" in result
        assert "<" not in result


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
