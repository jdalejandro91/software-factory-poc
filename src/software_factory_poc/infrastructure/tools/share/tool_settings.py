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

class ToolSettings(BaseSettings):
    # Security
    jira_webhook_secret: SecretStr = Field(..., description="Token to validate incoming Jira webhooks")

    # Jira Config
    jira_base_url: str = Field(..., description="Jira Base URL, e.g. https://myorg.atlassian.net")
    jira_auth_mode: JiraAuthMode = Field(default=JiraAuthMode.CLOUD_API_TOKEN)
    jira_user_email: str | None = None
    jira_api_token: SecretStr | None = None
    jira_bearer_token: SecretStr | None = None
    
    # Workflow Config
    jira_transition_in_review: str = Field(default="In Review", description="Name of the transition to move issue to In Review")

    # GitLab Config
    gitlab_base_url: str = "https://gitlab.com"
    gitlab_token: SecretStr | None = None

    # Confluence Config
    confluence_base_url: str = Field(..., description="Confluence Base URL")
    confluence_user_email: str = Field(default="jacadenac@unal.edu.co")
    confluence_api_token: SecretStr = Field(..., description="Confluence API Token")
    architecture_doc_page_id: str = Field(default="3571713")
    code_review_model: str = Field(default="openai:gpt-4-turbo", description="Model ID for Code Review Agent")
    code_review_llm_model_priority: str = Field(
        default='["openai:gpt-4-turbo"]', 
        description="JSON list of model IDs for Code Review"
    )

    def validate_jira_credentials(self) -> None:
        """
        Validates that the necessary credentials for the selected JiraAuthMode are present.
        """
        if self.jira_auth_mode == JiraAuthMode.CLOUD_API_TOKEN:
            if not self.jira_user_email:
                raise ValueError("JiraAuthMode.CLOUD_API_TOKEN requires 'jira_user_email'.")
            if not self.jira_api_token:
                raise ValueError("JiraAuthMode.CLOUD_API_TOKEN requires 'jira_api_token'.")
        
        elif self.jira_auth_mode == JiraAuthMode.BEARER:
            if not self.jira_bearer_token:
                raise ValueError("JiraAuthMode.BEARER requires 'jira_bearer_token'.")

        elif self.jira_auth_mode == JiraAuthMode.BASIC:
             if not self.jira_api_token:
                raise ValueError("JiraAuthMode.BASIC requires 'jira_api_token' (as password).")

    def validate_gitlab_credentials(self) -> None:
        if not self.gitlab_token:
            raise ValueError("GitLab token is missing in settings.")

    def validate_confluence_credentials(self) -> None:
        """Validates that Confluence credentials are present."""
        if not self.confluence_api_token:
            raise ValueError("Confluence API Token is required.")
        if not self.confluence_user_email:
            raise ValueError("Confluence User Email is required.")

    model_config = SettingsConfigDict(env_file=None, extra="ignore")
