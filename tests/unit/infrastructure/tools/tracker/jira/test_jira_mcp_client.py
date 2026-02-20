"""Unit tests — JiraMcpClient (zero I/O, fully mocked MCP stdio)."""

import json
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from mcp import McpError
from mcp.types import ErrorData
from pydantic import SecretStr

from software_factory_poc.core.application.tools import TrackerTool
from software_factory_poc.core.application.tools.common.exceptions import ProviderError
from software_factory_poc.infrastructure.tools.tracker.jira.config.jira_settings import (
    JiraSettings,
)
from software_factory_poc.infrastructure.tools.tracker.jira.jira_description_builder import (
    _append_to_adf,
    build_updated_description,
)
from software_factory_poc.infrastructure.tools.tracker.jira.jira_mcp_client import (
    JiraMcpClient,
)

BASE_MODULE = "software_factory_poc.infrastructure.tools.common.base_mcp_client"


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


def _make_settings(**overrides: Any) -> JiraSettings:
    defaults: dict[str, Any] = {
        "JIRA_API_TOKEN": SecretStr("atlassian-token-123"),
        "JIRA_USER_EMAIL": "bot@company.io",
        "JIRA_BASE_URL": "https://company.atlassian.net",
        "WORKFLOW_STATE_INITIAL": "To Do",
        "WORKFLOW_STATE_SUCCESS": "In Review",
        "MCP_ATLASSIAN_COMMAND": "npx",
        "MCP_ATLASSIAN_ARGS": ["@anthropic/mcp-server-atlassian"],
    }
    defaults.update(overrides)
    return JiraSettings(**defaults)


def _build_client(settings: JiraSettings | None = None) -> JiraMcpClient:
    return JiraMcpClient(settings=settings or _make_settings())


def _text_result(text: str) -> FakeCallToolResult:
    return FakeCallToolResult(content=[FakeTextContent(text=text)])


def _error_result(text: str) -> FakeCallToolResult:
    return FakeCallToolResult(content=[FakeTextContent(text=text)], isError=True)


def _transitions_json(*transitions: tuple[str, str, str]) -> str:
    """Build Jira transitions JSON. Each tuple: (id, name, to_name)."""
    return json.dumps(
        {
            "transitions": [
                {"id": tid, "name": name, "to": {"name": to_name}}
                for tid, name, to_name in transitions
            ]
        }
    )


def _jira_issue_json(
    *,
    key: str = "PROJ-1",
    issue_id: str = "10001",
    summary: str = "Implement feature X",
    status: str = "To Do",
    project_key: str = "PROJ",
    issue_type: str = "Story",
    description: str = "Build the scaffolding for service Y.",
) -> str:
    return json.dumps(
        {
            "id": issue_id,
            "key": key,
            "fields": {
                "summary": summary,
                "status": {"name": status},
                "project": {"key": project_key},
                "issuetype": {"name": issue_type},
                "description": description,
            },
        }
    )


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
        patch(f"{BASE_MODULE}.stdio_client", side_effect=fake_stdio_client),
        patch(f"{BASE_MODULE}.ClientSession", side_effect=fake_client_session),
    ):
        yield mock_session


# ══════════════════════════════════════════════════════════════════════
# Port compliance
# ══════════════════════════════════════════════════════════════════════


class TestPortCompliance:
    def test_implements_tracker_port(self) -> None:
        client = _build_client()
        assert isinstance(client, TrackerTool)
        assert isinstance(client, JiraMcpClient)


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
        monkeypatch.delenv("JIRA_API_TOKEN", raising=False)
        settings = JiraSettings(
            JIRA_BASE_URL="https://test.atlassian.net",
            JIRA_USER_EMAIL="user@test.io",
            MCP_ATLASSIAN_ARGS=["server"],
            _env_file=None,  # type: ignore[call-arg]
        )
        client = _build_client(settings)
        params = client._server_params()

        assert params.env is not None
        assert "ATLASSIAN_API_TOKEN" not in params.env


# ══════════════════════════════════════════════════════════════════════
# add_comment
# ══════════════════════════════════════════════════════════════════════


class TestAddComment:
    async def test_calls_jira_add_comment(self, mock_mcp: AsyncMock) -> None:
        mock_mcp.call_tool.return_value = _text_result("ok")
        client = _build_client()

        await client.add_comment("PROJ-1", "Build succeeded")

        mock_mcp.call_tool.assert_called_once_with(
            "jira_add_comment",
            arguments={"issue_key": "PROJ-1", "comment": "Build succeeded"},
        )


# ══════════════════════════════════════════════════════════════════════
# update_status
# ══════════════════════════════════════════════════════════════════════


class TestUpdateStatus:
    async def test_resolves_transition_by_name(self, mock_mcp: AsyncMock) -> None:
        mock_mcp.call_tool.side_effect = [
            _text_result(_transitions_json(("21", "In Progress", "In Progress"))),
            _text_result("ok"),
        ]
        client = _build_client()
        await client.update_status("PROJ-1", "In Progress")

        calls = mock_mcp.call_tool.call_args_list
        assert len(calls) == 2
        assert calls[0][0][0] == "jira_get_transitions"
        assert calls[1][0][0] == "jira_transition_issue"
        assert calls[1][1]["arguments"]["transition_id"] == "21"

    async def test_resolves_transition_by_to_name(self, mock_mcp: AsyncMock) -> None:
        mock_mcp.call_tool.side_effect = [
            _text_result(_transitions_json(("11", "Start Review", "In Review"))),
            _text_result("ok"),
        ]
        client = _build_client()
        await client.update_status("PROJ-1", "In Review")

        calls = mock_mcp.call_tool.call_args_list
        assert calls[1][1]["arguments"]["transition_id"] == "11"

    async def test_case_insensitive_match(self, mock_mcp: AsyncMock) -> None:
        mock_mcp.call_tool.side_effect = [
            _text_result(_transitions_json(("21", "In Progress", "In Progress"))),
            _text_result("ok"),
        ]
        client = _build_client()
        await client.update_status("PROJ-1", "in progress")

        calls = mock_mcp.call_tool.call_args_list
        assert calls[1][1]["arguments"]["transition_id"] == "21"

    async def test_no_match_raises_provider_error(self, mock_mcp: AsyncMock) -> None:
        mock_mcp.call_tool.return_value = _text_result(
            _transitions_json(("21", "In Progress", "In Progress"))
        )
        client = _build_client()

        with pytest.raises(ProviderError, match="Transition not found"):
            await client.update_status("PROJ-1", "Nonexistent Status")


# ══════════════════════════════════════════════════════════════════════
# update_task_description
# ══════════════════════════════════════════════════════════════════════


class TestUpdateTaskDescription:
    async def test_fetches_current_then_appends_yaml_block(self, mock_mcp: AsyncMock) -> None:
        issue_json = _jira_issue_json(description="Existing content.")
        mock_mcp.call_tool.side_effect = [
            _text_result(issue_json),  # jira_get_issue
            _text_result("ok"),  # jira_update_issue
        ]
        client = _build_client()

        await client.update_task_description("PROJ-1", "key: value")

        calls = mock_mcp.call_tool.call_args_list
        assert len(calls) == 2
        assert calls[0][0][0] == "jira_get_issue"
        assert calls[1][0][0] == "jira_update_issue"
        updated_desc = calls[1][1]["arguments"]["fields"]["description"]
        assert updated_desc == "Existing content.\n\n```yaml\nkey: value\n```"

    async def test_handles_empty_current_description(self, mock_mcp: AsyncMock) -> None:
        issue_json = _jira_issue_json(description="")
        mock_mcp.call_tool.side_effect = [
            _text_result(issue_json),  # jira_get_issue
            _text_result("ok"),  # jira_update_issue
        ]
        client = _build_client()

        await client.update_task_description("PROJ-1", "New content")

        calls = mock_mcp.call_tool.call_args_list
        updated_desc = calls[1][1]["arguments"]["fields"]["description"]
        assert updated_desc == "\n\n```yaml\nNew content\n```"

    async def test_handles_null_description_as_empty(self, mock_mcp: AsyncMock) -> None:
        raw = json.dumps({"id": "1", "key": "X-1", "fields": {"description": None}})
        mock_mcp.call_tool.side_effect = [
            _text_result(raw),
            _text_result("ok"),
        ]
        client = _build_client()

        await client.update_task_description("X-1", "appended")

        calls = mock_mcp.call_tool.call_args_list
        updated_desc = calls[1][1]["arguments"]["fields"]["description"]
        assert updated_desc == "\n\n```yaml\nappended\n```"

    async def test_handles_adf_dict_description(self, mock_mcp: AsyncMock) -> None:
        adf_doc: dict[str, Any] = {
            "type": "doc",
            "version": 1,
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Hello"}]}],
        }
        raw = json.dumps({"id": "1", "key": "A-1", "fields": {"description": adf_doc}})
        mock_mcp.call_tool.side_effect = [
            _text_result(raw),
            _text_result("ok"),
        ]
        client = _build_client()

        await client.update_task_description("A-1", "service: my-svc")

        calls = mock_mcp.call_tool.call_args_list
        updated = calls[1][1]["arguments"]["fields"]["description"]
        assert isinstance(updated, dict)
        assert updated["type"] == "doc"
        # Original paragraph preserved
        assert updated["content"][0]["type"] == "paragraph"
        # codeBlock appended
        code_block = updated["content"][-1]
        assert code_block["type"] == "codeBlock"
        assert code_block["attrs"]["language"] == "yaml"
        assert code_block["content"][0]["text"] == "service: my-svc"


# ══════════════════════════════════════════════════════════════════════
# _build_updated_description / _append_to_adf — ADF-safe helpers
# ══════════════════════════════════════════════════════════════════════


class TestBuildUpdatedDescription:
    def test_plain_string_wraps_in_yaml_block(self) -> None:
        result = build_updated_description("Existing.", "key: val")
        assert result == "Existing.\n\n```yaml\nkey: val\n```"

    def test_none_produces_yaml_block(self) -> None:
        result = build_updated_description(None, "text")
        assert result == "\n\n```yaml\ntext\n```"

    def test_adf_dict_returns_dict_with_code_block(self) -> None:
        adf: dict[str, Any] = {"type": "doc", "content": []}
        result = build_updated_description(adf, "hello")
        assert isinstance(result, dict)
        assert result["content"][-1]["type"] == "codeBlock"

    def test_adf_dict_is_not_mutated(self) -> None:
        adf: dict[str, Any] = {"type": "doc", "content": [{"type": "paragraph"}]}
        original_len = len(adf["content"])
        build_updated_description(adf, "text")
        assert len(adf["content"]) == original_len


class TestAppendToAdf:
    def test_appends_code_block_to_existing_content(self) -> None:
        adf: dict[str, Any] = {
            "type": "doc",
            "content": [{"type": "paragraph", "content": []}],
        }
        result = _append_to_adf(adf, "service: x")
        assert len(result["content"]) == 2
        block = result["content"][1]
        assert block["type"] == "codeBlock"
        assert block["attrs"]["language"] == "yaml"
        assert block["content"][0]["text"] == "service: x"

    def test_creates_content_list_when_missing(self) -> None:
        adf: dict[str, Any] = {"type": "doc", "version": 1}
        result = _append_to_adf(adf, "data")
        assert len(result["content"]) == 1
        assert result["content"][0]["type"] == "codeBlock"

    def test_deep_copies_input(self) -> None:
        inner = {"type": "text", "text": "original"}
        adf: dict[str, Any] = {
            "type": "doc",
            "content": [{"type": "paragraph", "content": [inner]}],
        }
        result = _append_to_adf(adf, "new")
        result["content"][0]["content"][0]["text"] = "mutated"
        assert inner["text"] == "original"


# ══════════════════════════════════════════════════════════════════════
# Agentic operations — get_mcp_tools
# ══════════════════════════════════════════════════════════════════════


class TestGetMcpTools:
    async def test_filters_and_renames_jira_tools(self, mock_mcp: AsyncMock) -> None:
        mock_mcp.list_tools.return_value = FakeListToolsResult(
            tools=[
                FakeTool(name="jira_get_issue", description="Gets an issue"),
                FakeTool(name="jira_add_comment", description="Adds a comment"),
                FakeTool(name="confluence_search", description="Not jira"),
            ]
        )
        client = _build_client()

        tools = await client.get_mcp_tools()

        assert len(tools) == 2
        assert tools[0]["type"] == "function"
        assert tools[0]["function"]["name"] == "tracker_get_issue"
        assert tools[0]["function"]["description"] == "Gets an issue"
        assert tools[1]["function"]["name"] == "tracker_add_comment"

    async def test_excludes_non_jira_tools(self, mock_mcp: AsyncMock) -> None:
        mock_mcp.list_tools.return_value = FakeListToolsResult(
            tools=[
                FakeTool(name="gitlab_create_branch"),
                FakeTool(name="confluence_get_page"),
            ]
        )
        client = _build_client()

        tools = await client.get_mcp_tools()
        assert tools == []


# ══════════════════════════════════════════════════════════════════════
# Agentic operations — execute_tool
# ══════════════════════════════════════════════════════════════════════


class TestExecuteTool:
    async def test_translates_tracker_prefix_to_jira(self, mock_mcp: AsyncMock) -> None:
        mock_mcp.call_tool.return_value = _text_result("result-data")
        client = _build_client()

        result = await client.execute_tool("tracker_get_issue", {"issue_key": "PROJ-1"})

        assert result == "result-data"
        call_args = mock_mcp.call_tool.call_args
        assert call_args[0][0] == "jira_get_issue"

    async def test_sanitizes_arguments_via_redactor(self, mock_mcp: AsyncMock) -> None:
        mock_mcp.call_tool.return_value = _text_result("ok")
        client = _build_client()

        await client.execute_tool("tracker_add_comment", {"issue_key": "X-1", "comment": "hi"})

        call_args = mock_mcp.call_tool.call_args
        payload = call_args[1]["arguments"]
        assert "issue_key" in payload


# ══════════════════════════════════════════════════════════════════════
# Error handling
# ══════════════════════════════════════════════════════════════════════


class TestErrorHandling:
    async def test_mcp_error_becomes_provider_error(self, mock_mcp: AsyncMock) -> None:
        mock_mcp.call_tool.side_effect = McpError(ErrorData(code=-32600, message="Invalid request"))
        client = _build_client()

        with pytest.raises(ProviderError, match="MCP protocol error"):
            await client.add_comment("FAIL-1", "text")

    async def test_connection_failure_becomes_provider_error(self, mock_mcp: AsyncMock) -> None:
        mock_mcp.call_tool.side_effect = ConnectionError("stdio pipe broken")
        client = _build_client()

        with pytest.raises(ProviderError, match="connection failure"):
            await client.add_comment("FAIL-2", "text")

    async def test_tool_is_error_becomes_provider_error(self, mock_mcp: AsyncMock) -> None:
        mock_mcp.call_tool.return_value = _error_result("Issue not found")
        client = _build_client()

        with pytest.raises(ProviderError, match="Tool .* returned error"):
            await client.add_comment("404-1", "text")

    async def test_provider_error_includes_provider_name(self, mock_mcp: AsyncMock) -> None:
        mock_mcp.call_tool.side_effect = RuntimeError("boom")
        client = _build_client()

        with pytest.raises(ProviderError) as exc_info:
            await client.add_comment("CRASH-1", "text")

        assert exc_info.value.provider == "JiraMCP"
        assert exc_info.value.retryable is True

    async def test_mcp_error_is_retryable(self, mock_mcp: AsyncMock) -> None:
        mock_mcp.call_tool.side_effect = McpError(ErrorData(code=-32603, message="Internal error"))
        client = _build_client()

        with pytest.raises(ProviderError) as exc_info:
            await client.update_status("X-1", "Done")

        assert exc_info.value.retryable is True

    async def test_tool_error_is_not_retryable(self, mock_mcp: AsyncMock) -> None:
        mock_mcp.call_tool.return_value = _error_result("Validation failed")
        client = _build_client()

        with pytest.raises(ProviderError) as exc_info:
            await client.update_task_description("X-1", "new desc")

        assert exc_info.value.retryable is False


# ══════════════════════════════════════════════════════════════════════
# MCP Lifecycle (connect / disconnect)
# ══════════════════════════════════════════════════════════════════════


@pytest.mark.usefixtures("mock_mcp")
class TestMcpLifecycle:
    async def test_connect_opens_persistent_session(self) -> None:
        client = _build_client()
        assert client._session is None

        await client.connect()

        assert client._session is not None
        assert client._exit_stack is not None

    async def test_disconnect_clears_session(self) -> None:
        client = _build_client()
        await client.connect()

        await client.disconnect()

        assert client._session is None
        assert client._exit_stack is None

    async def test_disconnect_is_idempotent(self) -> None:
        client = _build_client()
        await client.disconnect()  # Must not raise without prior connect

    async def test_disconnect_swallows_exit_stack_error(self) -> None:
        """disconnect() must never propagate exceptions from _exit_stack.aclose()."""
        client = _build_client()
        await client.connect()
        assert client._exit_stack is not None
        client._exit_stack.aclose = AsyncMock(side_effect=RuntimeError("npx zombie"))

        await client.disconnect()  # Must NOT raise

        assert client._session is None
        assert client._exit_stack is None
