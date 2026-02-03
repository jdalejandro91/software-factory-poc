from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .confluence_settings import ConfluenceSettings
from .gitlab_settings import GitLabSettings
from .jira_settings import JiraSettings
from .llm_settings import LlmSettings
from .scaffolding_settings import ScaffoldingSettings
from .tool_settings import ToolSettings


class AppConfig(BaseSettings):
    """
    Master configuration class combining all sub-settings.
    Implements Centralized Configuration Pattern.
    """
    confluence: ConfluenceSettings = Field(default_factory=ConfluenceSettings)
    jira: JiraSettings = Field(default_factory=JiraSettings)
    gitlab: GitLabSettings = Field(default_factory=GitLabSettings)
    llm: LlmSettings = Field(default_factory=LlmSettings)
    scaffolding: ScaffoldingSettings = Field(default_factory=ScaffoldingSettings)
    tools: ToolSettings = Field(default_factory=ToolSettings)

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )
