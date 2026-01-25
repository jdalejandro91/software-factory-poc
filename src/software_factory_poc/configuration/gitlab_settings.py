from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class GitLabSettings(BaseSettings):
    """
    Settings for GitLab integration.
    """
    base_url: str = Field(default="https://gitlab.com", description="GitLab Base URL")
    token: SecretStr | None = Field(default=None, description="GitLab Token")

    model_config = SettingsConfigDict(
        env_prefix="GITLAB_",
        case_sensitive=True,
        extra="ignore"
    )
