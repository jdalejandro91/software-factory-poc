import json

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfluenceSettings(BaseSettings):
    """Settings for Confluence integration and shared Atlassian MCP server."""

    # ── Core Confluence settings ──
    api_token: SecretStr | None = Field(default=None, alias="CONFLUENCE_API_TOKEN")
    user_email: str = Field(default="", alias="CONFLUENCE_USER_EMAIL")
    base_url: str = Field(default="", alias="CONFLUENCE_BASE_URL")
    sample_path: str = Field(default="", alias="CONFLUENCE_SAMPLE_PATH")
    architecture_doc_page_id: str = Field(default="3571713", alias="ARCHITECTURE_DOC_PAGE_ID")

    # ── Shared Atlassian MCP server configuration ──
    mcp_atlassian_command: str = Field(default="uvx", alias="MCP_ATLASSIAN_COMMAND")
    mcp_atlassian_args: list[str] = Field(default_factory=lambda: ["mcp-atlassian"], alias="MCP_ATLASSIAN_ARGS")

    @field_validator("mcp_atlassian_args", mode="before")
    @classmethod
    def parse_json_list(cls, value: object) -> list[str]:
        """Parse JSON string from .env into a Python list."""
        if isinstance(value, str):
            parsed = json.loads(value)
            if not isinstance(parsed, list):
                raise ValueError(f"Expected a JSON list, got {type(parsed).__name__}")
            return parsed
        if isinstance(value, list):
            return value
        return []

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
