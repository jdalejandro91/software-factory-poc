"""Unit tests — GitlabMcpClient (zero I/O, fully mocked MCP stdio)."""

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
from software_factory_poc.core.application.ports.vcs_port import VcsPort
from software_factory_poc.core.domain.delivery.commit_intent import CommitIntent
from software_factory_poc.core.domain.delivery.value_objects.branch_name import BranchName
from software_factory_poc.core.domain.delivery.value_objects.file_content import FileContent
from software_factory_poc.core.domain.quality.code_review_report import CodeReviewReport
from software_factory_poc.core.domain.quality.value_objects.review_comment import ReviewComment
from software_factory_poc.core.domain.quality.value_objects.review_severity import ReviewSeverity
from software_factory_poc.infrastructure.tools.vcs.gitlab.config.gitlab_settings import (
    GitLabSettings,
)
from software_factory_poc.infrastructure.tools.vcs.gitlab.gitlab_mcp_client import (
    GitlabMcpClient,
)

MODULE = "software_factory_poc.infrastructure.tools.vcs.gitlab.gitlab_mcp_client"


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


def _make_settings(**overrides: Any) -> GitLabSettings:
    defaults: dict[str, Any] = {
        "GITLAB_TOKEN": SecretStr("glpat-test-token"),
        "GITLAB_BASE_URL": "https://gitlab.example.com",
        "GITLAB_PROJECT_ID": "42",
        "ALLOWLISTED_GROUPS": "my-group",
        "MCP_GITLAB_COMMAND": "npx",
        "MCP_GITLAB_ARGS": ["@modelcontextprotocol/server-gitlab"],
    }
    defaults.update(overrides)
    return GitLabSettings(**defaults)


def _build_client(settings: GitLabSettings | None = None) -> GitlabMcpClient:
    return GitlabMcpClient(settings=settings or _make_settings())


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
    def test_implements_vcs_port(self) -> None:
        client = _build_client()
        assert isinstance(client, VcsPort)

    def test_constructor_extracts_project_id_from_settings(self) -> None:
        client = _build_client(_make_settings(GITLAB_PROJECT_ID="99"))
        assert client._project_id == "99"


# ══════════════════════════════════════════════════════════════════════
# _server_params — credential injection for official GitLab MCP server
# ══════════════════════════════════════════════════════════════════════


class TestServerParams:
    def test_injects_personal_access_token_and_api_url(self) -> None:
        client = _build_client()
        params = client._server_params()

        assert params.command == "npx"
        assert params.args == ["@modelcontextprotocol/server-gitlab"]
        assert params.env is not None
        assert params.env["GITLAB_PERSONAL_ACCESS_TOKEN"] == "glpat-test-token"
        assert params.env["GITLAB_API_URL"] == "https://gitlab.example.com"

    def test_skips_token_when_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("GITLAB_TOKEN", raising=False)
        settings = GitLabSettings(
            GITLAB_BASE_URL="https://gl.io",
            GITLAB_PROJECT_ID="1",
            MCP_GITLAB_ARGS=["server"],
            _env_file=None,  # type: ignore[call-arg]
        )
        client = _build_client(settings)
        params = client._server_params()

        assert params.env is not None
        assert "GITLAB_PERSONAL_ACCESS_TOKEN" not in params.env

    def test_env_is_copy_of_os_environ(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SENTINEL_VAR", "present")
        client = _build_client()
        params = client._server_params()

        assert params.env is not None
        assert params.env["SENTINEL_VAR"] == "present"


# ══════════════════════════════════════════════════════════════════════
# Scaffolding Flow
# ══════════════════════════════════════════════════════════════════════


class TestValidateBranchExistence:
    async def test_returns_true_when_branch_exists(self, mock_mcp: AsyncMock) -> None:
        mock_mcp.call_tool.return_value = _text_result('{"name": "feature/x"}')
        client = _build_client()

        assert await client.validate_branch_existence("feature/x") is True
        mock_mcp.call_tool.assert_called_once_with(
            "gitlab_get_branch",
            arguments={"project_id": "42", "branch": "feature/x"},
        )

    async def test_returns_false_when_branch_missing(self, mock_mcp: AsyncMock) -> None:
        mock_mcp.call_tool.side_effect = Exception("404 Not Found")
        client = _build_client()

        assert await client.validate_branch_existence("feature/y") is False


class TestCreateBranch:
    async def test_returns_web_url(self, mock_mcp: AsyncMock) -> None:
        mock_mcp.call_tool.return_value = _text_result(
            json.dumps({"web_url": "https://gitlab.example.com/tree/feature/new"})
        )
        client = _build_client()

        url = await client.create_branch("feature/new", ref="main")
        assert url == "https://gitlab.example.com/tree/feature/new"

    async def test_raw_fallback_on_non_json(self, mock_mcp: AsyncMock) -> None:
        mock_mcp.call_tool.return_value = _text_result("Branch created")
        client = _build_client()

        result = await client.create_branch("feature/raw")
        assert result == "Branch created"


class TestCreateMergeRequest:
    async def test_returns_mr_url(self, mock_mcp: AsyncMock) -> None:
        mock_mcp.call_tool.return_value = _text_result(
            json.dumps({"web_url": "https://gitlab.example.com/mr/1"})
        )
        client = _build_client()

        url = await client.create_merge_request("feature/a", "main", "Title", "Desc")
        assert url == "https://gitlab.example.com/mr/1"
        mock_mcp.call_tool.assert_called_once_with(
            "gitlab_create_merge_request",
            arguments={
                "project_id": "42",
                "source_branch": "feature/a",
                "target_branch": "main",
                "title": "Title",
                "description": "Desc",
            },
        )


# ══════════════════════════════════════════════════════════════════════
# Commit Operation
# ══════════════════════════════════════════════════════════════════════


class TestCommitChanges:
    async def test_returns_commit_hash(self, mock_mcp: AsyncMock) -> None:
        mock_mcp.call_tool.return_value = _text_result(json.dumps({"commit_hash": "abc123def"}))
        client = _build_client()

        intent = CommitIntent(
            branch=BranchName("feature/commit-test"),
            message="feat: add file",
            files=[FileContent(path="src/main.py", content="print('hi')", is_new=True)],
        )
        result = await client.commit_changes(intent)
        assert result == "abc123def"

        call_args = mock_mcp.call_tool.call_args
        assert call_args[0][0] == "gitlab_create_commit"
        payload = call_args[1]["arguments"]
        assert payload["branch"] == "feature/commit-test"
        assert payload["actions"][0]["action"] == "create"
        assert payload["actions"][0]["file_path"] == "src/main.py"

    async def test_empty_commit_raises_value_error(self, mock_mcp: AsyncMock) -> None:
        client = _build_client()
        intent = CommitIntent(
            branch=BranchName("feature/empty"),
            message="empty",
            files=[],
        )
        with pytest.raises(ValueError, match="Commit contains no files"):
            await client.commit_changes(intent)


# ══════════════════════════════════════════════════════════════════════
# Code Review Flow
# ══════════════════════════════════════════════════════════════════════


class TestGetMergeRequestDiff:
    async def test_returns_diff_text(self, mock_mcp: AsyncMock) -> None:
        mock_mcp.call_tool.return_value = _text_result("diff --git a/f.py b/f.py")
        client = _build_client()

        diff = await client.get_merge_request_diff("7")
        assert diff == "diff --git a/f.py b/f.py"
        mock_mcp.call_tool.assert_called_once_with(
            "gitlab_get_merge_request_changes",
            arguments={"project_id": "42", "merge_request_iid": "7"},
        )


class TestPublishReview:
    async def test_approved_review_posts_note_and_approves(self, mock_mcp: AsyncMock) -> None:
        mock_mcp.call_tool.return_value = _text_result("ok")
        client = _build_client()

        report = CodeReviewReport(is_approved=True, summary="Looks good", comments=[])
        await client.publish_review("10", report)

        calls = mock_mcp.call_tool.call_args_list
        assert len(calls) == 2
        assert calls[0][0][0] == "gitlab_create_merge_request_note"
        assert calls[1][0][0] == "gitlab_approve_merge_request"

    async def test_rejected_review_posts_note_and_comments_no_approval(
        self, mock_mcp: AsyncMock
    ) -> None:
        mock_mcp.call_tool.return_value = _text_result("ok")
        client = _build_client()

        comment = ReviewComment(
            file_path="src/bad.py",
            description="Null pointer risk",
            suggestion="Add None check",
            severity=ReviewSeverity.WARNING,
            line_number=42,
        )
        report = CodeReviewReport(is_approved=False, summary="Needs work", comments=[comment])
        await client.publish_review("11", report)

        calls = mock_mcp.call_tool.call_args_list
        # 1 note + 1 discussion comment = 2 calls (no approve)
        assert len(calls) == 2
        assert calls[0][0][0] == "gitlab_create_merge_request_note"
        assert calls[1][0][0] == "gitlab_create_merge_request_discussion"
        discussion_args = calls[1][1]["arguments"]
        assert discussion_args["file_path"] == "src/bad.py"
        assert discussion_args["line"] == 42


# ══════════════════════════════════════════════════════════════════════
# Agentic Operations
# ══════════════════════════════════════════════════════════════════════


class TestGetMcpTools:
    async def test_filters_and_renames_gitlab_tools(self, mock_mcp: AsyncMock) -> None:
        mock_mcp.list_tools.return_value = FakeListToolsResult(
            tools=[
                FakeTool(name="gitlab_create_branch", description="Creates a branch"),
                FakeTool(name="gitlab_list_issues", description="Lists issues"),
                FakeTool(name="jira_create_issue", description="Not gitlab"),
            ]
        )
        client = _build_client()

        tools = await client.get_mcp_tools()
        assert len(tools) == 2
        assert tools[0]["name"] == "vcs_create_branch"
        assert tools[1]["name"] == "vcs_list_issues"


class TestExecuteTool:
    async def test_injects_project_id_if_missing(self, mock_mcp: AsyncMock) -> None:
        mock_mcp.call_tool.return_value = _text_result("result")
        client = _build_client()

        await client.execute_tool("vcs_create_branch", {"branch": "feature/x"})
        call_args = mock_mcp.call_tool.call_args
        assert call_args[0][0] == "gitlab_create_branch"
        payload = call_args[1]["arguments"]
        assert payload["project_id"] == "42"


# ══════════════════════════════════════════════════════════════════════
# Error handling
# ══════════════════════════════════════════════════════════════════════


class TestErrorHandling:
    async def test_mcp_error_becomes_provider_error(self, mock_mcp: AsyncMock) -> None:
        mock_mcp.call_tool.side_effect = McpError(ErrorData(code=-32600, message="Invalid request"))
        client = _build_client()

        with pytest.raises(ProviderError, match="MCP protocol error"):
            await client.create_branch("feature/fail")

    async def test_connection_failure_becomes_provider_error(self, mock_mcp: AsyncMock) -> None:
        mock_mcp.call_tool.side_effect = ConnectionError("stdio pipe broken")
        client = _build_client()

        with pytest.raises(ProviderError, match="Connection failure"):
            await client.create_branch("feature/broken")

    async def test_tool_is_error_becomes_provider_error(self, mock_mcp: AsyncMock) -> None:
        mock_mcp.call_tool.return_value = _error_result("Permission denied")
        client = _build_client()

        with pytest.raises(ProviderError, match="Tool .* returned error"):
            await client.create_branch("feature/denied")

    async def test_provider_error_includes_provider_name(self, mock_mcp: AsyncMock) -> None:
        mock_mcp.call_tool.side_effect = RuntimeError("boom")
        client = _build_client()

        with pytest.raises(ProviderError) as exc_info:
            await client.create_branch("feature/crash")

        assert exc_info.value.provider == "GitLabMCP"
        assert exc_info.value.retryable is True
