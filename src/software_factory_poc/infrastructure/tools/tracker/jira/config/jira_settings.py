import json

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class JiraSettings(BaseSettings):
    """Settings for Jira integration and shared Atlassian MCP server."""

    # ── Core Jira settings ──
    api_token: SecretStr | None = Field(default=None, alias="JIRA_API_TOKEN")
    webhook_secret: SecretStr | None = Field(default=None, alias="JIRA_WEBHOOK_SECRET")
    base_url: str = Field(default="", alias="JIRA_BASE_URL")
    user_email: str = Field(default="", alias="JIRA_USER_EMAIL")

    # ── Workflow states ──
    workflow_state_initial: str = Field(default="To Do", alias="WORKFLOW_STATE_INITIAL")
    workflow_state_success: str = Field(default="In Review", alias="WORKFLOW_STATE_SUCCESS")

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
