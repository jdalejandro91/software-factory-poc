"""Integration tests — verify DI wiring produces a working GitlabMcpClient."""

import pytest
from pydantic import SecretStr

from software_factory_poc.core.application.tools import VcsTool
from software_factory_poc.infrastructure.tools.vcs.gitlab.config.gitlab_settings import (
    GitLabSettings,
)
from software_factory_poc.infrastructure.tools.vcs.gitlab.gitlab_mcp_client import (
    GitlabMcpClient,
)


class TestGitLabSettingsFromEnv:
    """Verify GitLabSettings loads and parses fields from env vars.env."""

    def test_parses_all_fields_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GITLAB_TOKEN", "glpat-env-test")
        monkeypatch.setenv("GITLAB_BASE_URL", "https://gl.corp.io")
        monkeypatch.setenv("GITLAB_PROJECT_ID", "123")
        monkeypatch.setenv("ALLOWLISTED_GROUPS", "infra-team")
        monkeypatch.setenv("MCP_GITLAB_COMMAND", "node")
        monkeypatch.setenv("MCP_GITLAB_ARGS", '["server.js", "--port", "3000"]')

        settings = GitLabSettings()

        assert settings.token is not None
        assert settings.token.get_secret_value() == "glpat-env-test"
        assert settings.base_url == "https://gl.corp.io"
        assert settings.project_id == "123"
        assert settings.allowlisted_groups == "infra-team"
        assert settings.mcp_gitlab_command == "node"
        assert settings.mcp_gitlab_args == ["server.js", "--port", "3000"]

    def test_defaults_when_no_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for var in (
            "GITLAB_TOKEN",
            "GITLAB_BASE_URL",
            "GITLAB_PROJECT_ID",
            "ALLOWLISTED_GROUPS",
            "MCP_GITLAB_COMMAND",
            "MCP_GITLAB_ARGS",
        ):
            monkeypatch.delenv(var, raising=False)

        settings = GitLabSettings(_env_file=None)  # type: ignore[call-arg]

        assert settings.token is None
        assert settings.base_url == "https://gitlab.com"
        assert settings.project_id == ""
        assert settings.mcp_gitlab_command == "npx"
        assert settings.mcp_gitlab_args == []

    def test_mcp_args_accepts_native_list(self) -> None:
        settings = GitLabSettings(
            GITLAB_TOKEN=SecretStr("glpat-x"),
            GITLAB_PROJECT_ID="1",
            MCP_GITLAB_ARGS=["arg1", "arg2"],
        )
        assert settings.mcp_gitlab_args == ["arg1", "arg2"]


class TestGitLabMcpClientWiring:
    """Verify that building GitlabMcpClient through GitLabSettings yields a valid VcsTool."""

    def test_client_from_settings_is_vcs_port(self) -> None:
        settings = GitLabSettings(
            GITLAB_TOKEN=SecretStr("glpat-wiring"),
            GITLAB_PROJECT_ID="99",
            GITLAB_BASE_URL="https://gl.test",
            MCP_GITLAB_ARGS=["server-gitlab"],
        )

        client = GitlabMcpClient(settings=settings)

        assert isinstance(client, VcsTool)
        assert isinstance(client, GitlabMcpClient)
        assert client._project_id == "99"
