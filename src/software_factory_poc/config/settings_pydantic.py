from enum import StrEnum
from pathlib import Path
from typing import List, Optional

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings

from software_factory_poc.config.allowlists_config import (
    DEFAULT_ALLOWLISTED_GITLAB_PROJECT_IDS,
    DEFAULT_ALLOWLISTED_TEMPLATE_IDS,
    DEFAULT_PROTECTED_BRANCHES,
)


class JiraAuthMode(StrEnum):
    CLOUD_API_TOKEN = "cloud_api_token"
    BEARER = "bearer"
    BASIC = "basic"


class Settings(BaseSettings):
    # App Config
    app_name: str = "Software Factory PoC"
    log_level: str = "INFO"

    # Security
    jira_webhook_secret: SecretStr = Field(..., description="Token to validate incoming Jira webhooks")

    # Jira Config
    jira_base_url: str = Field(..., description="Jira Base URL, e.g. https://myorg.atlassian.net")
    jira_auth_mode: JiraAuthMode = Field(default=JiraAuthMode.CLOUD_API_TOKEN)
    jira_user_email: Optional[str] = None
    jira_api_token: Optional[SecretStr] = None
    jira_bearer_token: Optional[SecretStr] = None

    # GitLab Config
    gitlab_base_url: str = "https://gitlab.com"
    gitlab_token: Optional[SecretStr] = None

    # Templates & Filesystem
    template_catalog_root: Path = Field(
        default=Path("src/software_factory_poc/templates/template_catalog")
    )
    runtime_data_dir: Path = Field(default=Path("runtime_data"))

    # Policies / Constraints
    default_target_base_branch: str = "main"
    
    allowlisted_template_ids: List[str] = Field(
        default_factory=lambda: DEFAULT_ALLOWLISTED_TEMPLATE_IDS
    )
    allowlisted_gitlab_project_ids: List[int] = Field(
        default_factory=lambda: DEFAULT_ALLOWLISTED_GITLAB_PROJECT_IDS
    )
    allowlisted_groups: List[str] = ["jdalejandro91-group"] # Default allowed namespace
    protected_branches: List[str] = Field(
        default_factory=lambda: DEFAULT_PROTECTED_BRANCHES
    )

    def validate_jira_credentials(self) -> None:
        """
        Validates that the necessary credentials for the selected JiraAuthMode are present.
        Does NOT log values. Raises ValueError if missing.
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
             if not self.jira_api_token: # Assuming Basic uses token as password usually
                raise ValueError("JiraAuthMode.BASIC requires 'jira_api_token' (as password).")

    def validate_gitlab_credentials(self) -> None:
        if not self.gitlab_token:
            # We allow it to be None if we are just testing unrelated things, 
            # but usually we want to enforce it if calling gitlab.
            # This method can be called explicitly when starting a GitLab flow.
            raise ValueError("GitLab token is missing in settings.")

    model_config = {
        "env_file": None, # Explicitly do not read .env automatically as per requirements
        "extra": "ignore"
    }

# Global singleton is not strictly required if we use dependency injection, 
# but instantiating it once to validate ENV early is good practice.
# However, we will let 'main.py' or 'app_factory.py' instantiate it.
