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

from software_factory_poc.core.application.ports.common.exceptions.provider_error import (
    ProviderError,
)
from software_factory_poc.core.application.ports.tracker_port import TrackerPort
from software_factory_poc.core.domain.mission.entities.mission import Mission
from software_factory_poc.core.domain.mission.value_objects.task_description import TaskDescription
from software_factory_poc.core.domain.quality.code_review_report import CodeReviewReport
from software_factory_poc.core.domain.quality.value_objects.review_comment import ReviewComment
from software_factory_poc.core.domain.quality.value_objects.review_severity import ReviewSeverity
from software_factory_poc.infrastructure.observability.redaction_service import RedactionService
from software_factory_poc.infrastructure.tools.tracker.jira.config.jira_settings import (
    JiraSettings,
)
from software_factory_poc.infrastructure.tools.tracker.jira.jira_mcp_client import (
    JiraMcpClient,
)

MODULE = "software_factory_poc.infrastructure.tools.tracker.jira.jira_mcp_client"


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
    return JiraMcpClient(
        settings=settings or _make_settings(),
        redactor=RedactionService(),
    )


def _text_result(text: str) -> FakeCallToolResult:
    return FakeCallToolResult(content=[FakeTextContent(text=text)])


def _error_result(text: str) -> FakeCallToolResult:
    return FakeCallToolResult(content=[FakeTextContent(text=text)], isError=True)


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
        patch(f"{MODULE}.stdio_client", side_effect=fake_stdio_client),
        patch(f"{MODULE}.ClientSession", side_effect=fake_client_session),
    ):
        yield mock_session


# ══════════════════════════════════════════════════════════════════════
# Port compliance
# ══════════════════════════════════════════════════════════════════════


class TestPortCompliance:
    def test_implements_tracker_port(self) -> None:
        client = _build_client()
        assert isinstance(client, TrackerPort)
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
# _parse_description — YAML config extraction
# ══════════════════════════════════════════════════════════════════════


class TestParseDescription:
    def test_empty_text_returns_empty_task_description(self) -> None:
        result = JiraMcpClient._parse_description("")
        assert result == TaskDescription(raw_content="", config={})

    def test_none_text_returns_empty_task_description(self) -> None:
        result = JiraMcpClient._parse_description("")
        assert result.raw_content == ""
        assert result.config == {}

    def test_plain_text_without_config_block(self) -> None:
        text = "Implement REST API for user management."
        result = JiraMcpClient._parse_description(text)
        assert result.raw_content == text
        assert result.config == {}

    def test_extracts_scaffolder_yaml_block(self) -> None:
        text = (
            "Build microservice.\n\n"
            "```scaffolder\n"
            "language: python\n"
            "framework: fastapi\n"
            "```\n\n"
            "Additional notes here."
        )
        result = JiraMcpClient._parse_description(text)
        assert result.config == {"language": "python", "framework": "fastapi"}
        assert "Build microservice." in result.raw_content
        assert "Additional notes here." in result.raw_content
        assert "```scaffolder" not in result.raw_content

    def test_extracts_yaml_block(self) -> None:
        text = "Description.\n\n```yaml\nmerge_request_iid: 42\n```"
        result = JiraMcpClient._parse_description(text)
        assert result.config == {"merge_request_iid": 42}
        assert "```yaml" not in result.raw_content

    def test_extracts_yml_block(self) -> None:
        text = "Some text.\n\n```yml\nkey: value\n```"
        result = JiraMcpClient._parse_description(text)
        assert result.config == {"key": "value"}

    def test_invalid_yaml_falls_back_to_empty_config(self) -> None:
        text = "Desc.\n\n```yaml\n: invalid: yaml: {{{\n```"
        result = JiraMcpClient._parse_description(text)
        assert result.config == {}
        assert "Desc." in result.raw_content

    def test_non_dict_yaml_ignored(self) -> None:
        text = "Desc.\n\n```yaml\n- item1\n- item2\n```"
        result = JiraMcpClient._parse_description(text)
        assert result.config == {}


# ══════════════════════════════════════════════════════════════════════
# get_task — JSON-RPC to Mission mapping
# ══════════════════════════════════════════════════════════════════════


class TestGetTask:
    async def test_maps_jira_issue_to_mission(self, mock_mcp: AsyncMock) -> None:
        mock_mcp.call_tool.return_value = _text_result(_jira_issue_json())
        client = _build_client()

        mission = await client.get_task("PROJ-1")

        assert isinstance(mission, Mission)
        assert mission.id == "10001"
        assert mission.key == "PROJ-1"
        assert mission.summary == "Implement feature X"
        assert mission.status == "To Do"
        assert mission.project_key == "PROJ"
        assert mission.issue_type == "Story"
        assert mission.description.raw_content == "Build the scaffolding for service Y."
        assert mission.description.config == {}

        mock_mcp.call_tool.assert_called_once_with(
            "jira_get_issue",
            arguments={"issue_key": "PROJ-1"},
        )

    async def test_maps_description_with_yaml_config(self, mock_mcp: AsyncMock) -> None:
        desc = "Task text.\n\n```scaffolder\nlanguage: java\n```"
        mock_mcp.call_tool.return_value = _text_result(_jira_issue_json(description=desc))
        client = _build_client()

        mission = await client.get_task("PROJ-2")

        assert mission.description.config == {"language": "java"}
        assert "Task text." in mission.description.raw_content
        assert "```scaffolder" not in mission.description.raw_content

    async def test_handles_empty_description(self, mock_mcp: AsyncMock) -> None:
        mock_mcp.call_tool.return_value = _text_result(_jira_issue_json(description=""))
        client = _build_client()

        mission = await client.get_task("PROJ-3")

        assert mission.description.raw_content == ""
        assert mission.description.config == {}

    async def test_handles_null_description(self, mock_mcp: AsyncMock) -> None:
        raw = json.dumps(
            {
                "id": "1",
                "key": "X-1",
                "fields": {
                    "summary": "s",
                    "status": {"name": "Open"},
                    "project": {"key": "X"},
                    "issuetype": {"name": "Bug"},
                    "description": None,
                },
            }
        )
        mock_mcp.call_tool.return_value = _text_result(raw)
        client = _build_client()

        mission = await client.get_task("X-1")
        assert mission.description == TaskDescription(raw_content="", config={})

    async def test_defaults_when_fields_missing(self, mock_mcp: AsyncMock) -> None:
        raw = json.dumps({"id": "1", "key": "M-1"})
        mock_mcp.call_tool.return_value = _text_result(raw)
        client = _build_client()

        mission = await client.get_task("M-1")

        assert mission.summary == ""
        assert mission.status == "OPEN"
        assert mission.project_key == ""
        assert mission.issue_type == "Task"

    async def test_non_json_response_raises_provider_error(self, mock_mcp: AsyncMock) -> None:
        mock_mcp.call_tool.return_value = _text_result("not json at all")
        client = _build_client()

        with pytest.raises(ProviderError, match="Non-JSON response"):
            await client.get_task("BAD-1")


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
    async def test_calls_jira_transition_issue(self, mock_mcp: AsyncMock) -> None:
        mock_mcp.call_tool.return_value = _text_result("ok")
        client = _build_client()

        await client.update_status("PROJ-1", "In Progress")

        mock_mcp.call_tool.assert_called_once_with(
            "jira_transition_issue",
            arguments={"issue_key": "PROJ-1", "transition_name": "In Progress"},
        )


# ══════════════════════════════════════════════════════════════════════
# update_task_description
# ══════════════════════════════════════════════════════════════════════


class TestUpdateTaskDescription:
    async def test_calls_jira_update_issue(self, mock_mcp: AsyncMock) -> None:
        mock_mcp.call_tool.return_value = _text_result("ok")
        client = _build_client()

        await client.update_task_description("PROJ-1", "New description content")

        mock_mcp.call_tool.assert_called_once_with(
            "jira_update_issue",
            arguments={
                "issue_key": "PROJ-1",
                "fields": {"description": "New description content"},
            },
        )


# ══════════════════════════════════════════════════════════════════════
# post_review_summary
# ══════════════════════════════════════════════════════════════════════


class TestPostReviewSummary:
    async def test_approved_transitions_to_success_state(self, mock_mcp: AsyncMock) -> None:
        mock_mcp.call_tool.return_value = _text_result("ok")
        client = _build_client()

        report = CodeReviewReport(is_approved=True, summary="Looks good", comments=[])
        await client.post_review_summary("PROJ-1", report)

        calls = mock_mcp.call_tool.call_args_list
        # 1. transition + 2. add_comment = 2 calls
        assert len(calls) == 2
        assert calls[0][0][0] == "jira_transition_issue"
        assert calls[0][1]["arguments"]["transition_name"] == "In Review"
        assert calls[1][0][0] == "jira_add_comment"

    async def test_rejected_transitions_to_initial_state(self, mock_mcp: AsyncMock) -> None:
        mock_mcp.call_tool.return_value = _text_result("ok")
        client = _build_client()

        report = CodeReviewReport(is_approved=False, summary="Needs work", comments=[])
        await client.post_review_summary("PROJ-2", report)

        calls = mock_mcp.call_tool.call_args_list
        assert calls[0][1]["arguments"]["transition_name"] == "To Do"

    async def test_approved_comment_contains_approved_label(self, mock_mcp: AsyncMock) -> None:
        mock_mcp.call_tool.return_value = _text_result("ok")
        client = _build_client()

        report = CodeReviewReport(is_approved=True, summary="All clear", comments=[])
        await client.post_review_summary("PROJ-1", report)

        comment_arg = mock_mcp.call_tool.call_args_list[1][1]["arguments"]["comment"]
        assert "APPROVED" in comment_arg

    async def test_rejected_comment_contains_changes_requested(self, mock_mcp: AsyncMock) -> None:
        mock_mcp.call_tool.return_value = _text_result("ok")
        client = _build_client()

        report = CodeReviewReport(is_approved=False, summary="Issues found", comments=[])
        await client.post_review_summary("PROJ-1", report)

        comment_arg = mock_mcp.call_tool.call_args_list[1][1]["arguments"]["comment"]
        assert "CHANGES REQUESTED" in comment_arg

    async def test_findings_table_in_comment(self, mock_mcp: AsyncMock) -> None:
        mock_mcp.call_tool.return_value = _text_result("ok")
        client = _build_client()

        comment = ReviewComment(
            file_path="src/main.py",
            description="SQL injection risk",
            suggestion="Use parameterized queries",
            severity=ReviewSeverity.WARNING,
            line_number=42,
        )
        report = CodeReviewReport(is_approved=False, summary="Security issues", comments=[comment])
        await client.post_review_summary("PROJ-1", report)

        comment_md = mock_mcp.call_tool.call_args_list[1][1]["arguments"]["comment"]
        assert "### Findings" in comment_md
        assert "**WARNING**" in comment_md
        assert "`src/main.py:42`" in comment_md
        assert "SQL injection risk" in comment_md

    async def test_uses_custom_workflow_states(self, mock_mcp: AsyncMock) -> None:
        mock_mcp.call_tool.return_value = _text_result("ok")
        settings = _make_settings(
            WORKFLOW_STATE_SUCCESS="Done",
            WORKFLOW_STATE_INITIAL="Backlog",
        )
        client = _build_client(settings)

        report = CodeReviewReport(is_approved=True, summary="OK", comments=[])
        await client.post_review_summary("PROJ-1", report)

        calls = mock_mcp.call_tool.call_args_list
        assert calls[0][1]["arguments"]["transition_name"] == "Done"


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
        assert tools[0]["name"] == "tracker_get_issue"
        assert tools[0]["description"] == "Gets an issue"
        assert tools[1]["name"] == "tracker_add_comment"

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
            await client.get_task("FAIL-1")

    async def test_connection_failure_becomes_provider_error(self, mock_mcp: AsyncMock) -> None:
        mock_mcp.call_tool.side_effect = ConnectionError("stdio pipe broken")
        client = _build_client()

        with pytest.raises(ProviderError, match="Connection failure"):
            await client.add_comment("FAIL-2", "text")

    async def test_tool_is_error_becomes_provider_error(self, mock_mcp: AsyncMock) -> None:
        mock_mcp.call_tool.return_value = _error_result("Issue not found")
        client = _build_client()

        with pytest.raises(ProviderError, match="Tool .* returned error"):
            await client.get_task("404-1")

    async def test_provider_error_includes_provider_name(self, mock_mcp: AsyncMock) -> None:
        mock_mcp.call_tool.side_effect = RuntimeError("boom")
        client = _build_client()

        with pytest.raises(ProviderError) as exc_info:
            await client.get_task("CRASH-1")

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
