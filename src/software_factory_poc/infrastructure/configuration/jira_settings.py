try:
    from enum import StrEnum
except ImportError:
    from enum import Enum
    class StrEnum(str, Enum):
        pass
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class JiraAuthMode(StrEnum):
    CLOUD_API_TOKEN = "cloud_api_token"
    BEARER = "bearer"
    BASIC = "basic"

class JiraSettings(BaseSettings):
    """
    Settings for Jira integration.
    """
    base_url: str = Field(..., description="Jira Base URL")
    auth_mode: JiraAuthMode = Field(default=JiraAuthMode.CLOUD_API_TOKEN)
    user_email: str | None = Field(default=None)
    api_token: SecretStr | None = Field(default=None)
    bearer_token: SecretStr | None = Field(default=None)
    webhook_secret: SecretStr = Field(..., description="Token to validate incoming Jira webhooks")

    def validate_credentials(self) -> None:
        """
        Validates that the necessary credentials for the selected JiraAuthMode are present.
        """
        if self.auth_mode == JiraAuthMode.CLOUD_API_TOKEN:
            if not self.user_email:
                raise ValueError("JiraAuthMode.CLOUD_API_TOKEN requires 'user_email'.")
            if not self.api_token:
                raise ValueError("JiraAuthMode.CLOUD_API_TOKEN requires 'api_token'.")
        
        elif self.auth_mode == JiraAuthMode.BEARER:
            if not self.bearer_token:
                raise ValueError("JiraAuthMode.BEARER requires 'bearer_token'.")

        elif self.auth_mode == JiraAuthMode.BASIC:
             if not self.api_token:
                raise ValueError("JiraAuthMode.BASIC requires 'api_token' (as password).")

    model_config = SettingsConfigDict(
        env_prefix="JIRA_",
        case_sensitive=False,
        extra="ignore"
    )
