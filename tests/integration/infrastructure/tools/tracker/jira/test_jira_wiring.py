"""Integration tests — verify DI wiring produces a working JiraMcpClient."""

import pytest
from pydantic import SecretStr

from software_factory_poc.core.application.ports.tracker_port import TrackerPort
from software_factory_poc.infrastructure.tools.tracker.jira.config.jira_settings import (
    JiraSettings,
)
from software_factory_poc.infrastructure.tools.tracker.jira.jira_mcp_client import (
    JiraMcpClient,
)


class TestJiraSettingsFromEnv:
    """Verify JiraSettings loads and parses fields from env vars."""

    def test_parses_all_fields_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("JIRA_API_TOKEN", "atlassian-env-test")
        monkeypatch.setenv("JIRA_BASE_URL", "https://corp.atlassian.net")
        monkeypatch.setenv("JIRA_USER_EMAIL", "bot@corp.io")
        monkeypatch.setenv("WORKFLOW_STATE_INITIAL", "Backlog")
        monkeypatch.setenv("WORKFLOW_STATE_SUCCESS", "Done")
        monkeypatch.setenv("MCP_ATLASSIAN_COMMAND", "node")
        monkeypatch.setenv("MCP_ATLASSIAN_ARGS", '["server.js", "--port", "3000"]')

        settings = JiraSettings()

        assert settings.api_token is not None
        assert settings.api_token.get_secret_value() == "atlassian-env-test"
        assert settings.base_url == "https://corp.atlassian.net"
        assert settings.user_email == "bot@corp.io"
        assert settings.workflow_state_initial == "Backlog"
        assert settings.workflow_state_success == "Done"
        assert settings.mcp_atlassian_command == "node"
        assert settings.mcp_atlassian_args == ["server.js", "--port", "3000"]

    def test_defaults_when_no_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for var in (
            "JIRA_API_TOKEN",
            "JIRA_WEBHOOK_SECRET",
            "JIRA_BASE_URL",
            "JIRA_USER_EMAIL",
            "WORKFLOW_STATE_INITIAL",
            "WORKFLOW_STATE_SUCCESS",
            "MCP_ATLASSIAN_COMMAND",
            "MCP_ATLASSIAN_ARGS",
        ):
            monkeypatch.delenv(var, raising=False)

        settings = JiraSettings(_env_file=None)  # type: ignore[call-arg]

        assert settings.api_token is None
        assert settings.base_url == ""
        assert settings.user_email == ""
        assert settings.workflow_state_initial == "To Do"
        assert settings.workflow_state_success == "In Review"
        assert settings.mcp_atlassian_command == "npx"
        assert settings.mcp_atlassian_args == []

    def test_mcp_args_accepts_native_list(self) -> None:
        settings = JiraSettings(
            JIRA_API_TOKEN=SecretStr("atlassian-x"),
            MCP_ATLASSIAN_ARGS=["arg1", "arg2"],
        )
        assert settings.mcp_atlassian_args == ["arg1", "arg2"]


class TestJiraMcpClientWiring:
    """Verify that building JiraMcpClient through JiraSettings yields a valid TrackerPort."""

    def test_client_from_settings_is_tracker_port(self) -> None:
        settings = JiraSettings(
            JIRA_API_TOKEN=SecretStr("atlassian-wiring"),
            JIRA_BASE_URL="https://test.atlassian.net",
            JIRA_USER_EMAIL="user@test.io",
            MCP_ATLASSIAN_ARGS=["@anthropic/mcp-server-atlassian"],
        )

        client = JiraMcpClient(settings=settings)

        assert isinstance(client, TrackerPort)
        assert isinstance(client, JiraMcpClient)
