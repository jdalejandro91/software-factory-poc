from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from software_factory_poc.infrastructure.configuration.agents.scaffolder.scaffolding_settings import (
    ScaffoldingSettings,
)
from software_factory_poc.infrastructure.configuration.tools.confluence.confluence_settings import (
    ConfluenceSettings,
)
from software_factory_poc.infrastructure.configuration.tools.gitlab import GitLabSettings
from software_factory_poc.infrastructure.configuration.tools.jira.jira_settings import JiraSettings
from software_factory_poc.infrastructure.configuration.tools.llm.llm_settings import LlmSettings
from software_factory_poc.infrastructure.configuration.tools.tool_settings import ToolSettings


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
