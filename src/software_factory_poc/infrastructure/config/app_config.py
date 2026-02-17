from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from software_factory_poc.infrastructure.config.agents.scaffolder.scaffolding_settings import (
    ScaffoldingSettings,
)
from software_factory_poc.infrastructure.tools.docs.config.confluence_settings import (
    ConfluenceSettings,
)
from software_factory_poc.infrastructure.tools.llm.config.llm_settings import LlmSettings
from software_factory_poc.infrastructure.tools.share.tool_settings import ToolSettings
from software_factory_poc.infrastructure.tools.tracker.jira.config.jira_settings import JiraSettings
from software_factory_poc.infrastructure.tools.vcs.config.gitlab_settings import GitLabSettings


class AppConfig(BaseSettings):
    """
    Master config class combining all sub-settings.
    Implements Centralized Configuration Pattern.
    """

    confluence: ConfluenceSettings = Field(default_factory=ConfluenceSettings)  # type: ignore[arg-type]
    jira: JiraSettings = Field(default_factory=JiraSettings)  # type: ignore[arg-type]
    gitlab: GitLabSettings = Field(default_factory=GitLabSettings)
    llm: LlmSettings = Field(default_factory=LlmSettings)
    scaffolding: ScaffoldingSettings = Field(default_factory=ScaffoldingSettings)
    tools: ToolSettings = Field(default_factory=ToolSettings)  # type: ignore[arg-type]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
