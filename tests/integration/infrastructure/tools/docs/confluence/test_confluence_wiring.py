"""Integration tests — verify DI wiring produces a working ConfluenceMcpClient."""

import pytest
from pydantic import SecretStr

from software_factory_poc.core.application.ports import DocsPort
from software_factory_poc.infrastructure.tools.docs.confluence.config.confluence_settings import (
    ConfluenceSettings,
)
from software_factory_poc.infrastructure.tools.docs.confluence.confluence_mcp_client import (
    ConfluenceMcpClient,
)


class TestConfluenceSettingsFromEnv:
    """Verify ConfluenceSettings loads and parses fields from env vars."""

    def test_parses_all_fields_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CONFLUENCE_API_TOKEN", "tok-env-test")
        monkeypatch.setenv("CONFLUENCE_USER_EMAIL", "ci@corp.io")
        monkeypatch.setenv("CONFLUENCE_BASE_URL", "https://corp.atlassian.net")
        monkeypatch.setenv("ARCHITECTURE_DOC_PAGE_ID", "7777")
        monkeypatch.setenv("MCP_ATLASSIAN_COMMAND", "node")
        monkeypatch.setenv("MCP_ATLASSIAN_ARGS", '["server.js", "--confluence"]')

        settings = ConfluenceSettings()

        assert settings.api_token is not None
        assert settings.api_token.get_secret_value() == "tok-env-test"
        assert settings.user_email == "ci@corp.io"
        assert settings.base_url == "https://corp.atlassian.net"
        assert settings.architecture_doc_page_id == "7777"
        assert settings.mcp_atlassian_command == "node"
        assert settings.mcp_atlassian_args == ["server.js", "--confluence"]

    def test_defaults_when_no_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for var in (
            "CONFLUENCE_API_TOKEN",
            "CONFLUENCE_USER_EMAIL",
            "CONFLUENCE_BASE_URL",
            "ARCHITECTURE_DOC_PAGE_ID",
            "MCP_ATLASSIAN_COMMAND",
            "MCP_ATLASSIAN_ARGS",
        ):
            monkeypatch.delenv(var, raising=False)

        settings = ConfluenceSettings(_env_file=None)  # type: ignore[call-arg]

        assert settings.api_token is None
        assert settings.user_email == ""
        assert settings.base_url == ""
        assert settings.architecture_doc_page_id == "3571713"
        assert settings.mcp_atlassian_command == "npx"
        assert settings.mcp_atlassian_args == []

    def test_mcp_args_accepts_native_list(self) -> None:
        settings = ConfluenceSettings(
            CONFLUENCE_API_TOKEN=SecretStr("tok-x"),
            CONFLUENCE_USER_EMAIL="user@x.io",
            CONFLUENCE_BASE_URL="https://x.atlassian.net",
            MCP_ATLASSIAN_ARGS=["arg1", "arg2"],
        )
        assert settings.mcp_atlassian_args == ["arg1", "arg2"]


class TestConfluenceMcpClientWiring:
    """Verify that building ConfluenceMcpClient from ConfluenceSettings yields a valid DocsPort."""

    def test_client_from_settings_is_docs_port(self) -> None:
        settings = ConfluenceSettings(
            CONFLUENCE_API_TOKEN=SecretStr("tok-wiring"),
            CONFLUENCE_USER_EMAIL="bot@test.io",
            CONFLUENCE_BASE_URL="https://test.atlassian.net",
            MCP_ATLASSIAN_ARGS=["@anthropic/mcp-server-atlassian"],
        )

        client = ConfluenceMcpClient(settings=settings)

        assert isinstance(client, DocsPort)
        assert isinstance(client, ConfluenceMcpClient)
