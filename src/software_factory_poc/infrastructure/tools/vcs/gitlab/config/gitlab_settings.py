import json

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class GitLabSettings(BaseSettings):
    """Settings for GitLab integration and MCP server configuration."""

    # ── Core GitLab settings ──
    base_url: str = Field(default="https://gitlab.com", alias="GITLAB_BASE_URL")
    token: SecretStr | None = Field(default=None, alias="GITLAB_TOKEN")
    project_id: str = Field(default="", alias="GITLAB_PROJECT_ID")
    allowlisted_groups: str = Field(default="", alias="ALLOWLISTED_GROUPS")

    # ── MCP server configuration ──
    mcp_gitlab_command: str = Field(default="npx", alias="MCP_GITLAB_COMMAND")
    mcp_gitlab_args: list[str] = Field(default_factory=list, alias="MCP_GITLAB_ARGS")

    @field_validator("mcp_gitlab_args", mode="before")
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
