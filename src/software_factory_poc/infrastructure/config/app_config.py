from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from software_factory_poc.infrastructure.adapters.llm.config.llm_settings import LlmSettings
from software_factory_poc.infrastructure.config.agents.scaffolder.scaffolding_settings import (
    ScaffoldingSettings,
)
from software_factory_poc.infrastructure.tools.docs.confluence.config.confluence_settings import (
    ConfluenceSettings,
)
from software_factory_poc.infrastructure.tools.tracker.jira.config.jira_settings import JiraSettings
from software_factory_poc.infrastructure.tools.vcs.gitlab.config.gitlab_settings import (
    GitLabSettings,
)


class AppConfig(BaseSettings):
    """
    Master config class combining all sub-settings.
    Implements Centralized Configuration Pattern.
    """

    confluence: ConfluenceSettings = Field(default_factory=ConfluenceSettings)
    jira: JiraSettings = Field(default_factory=JiraSettings)
    gitlab: GitLabSettings = Field(default_factory=GitLabSettings)
    llm: LlmSettings = Field(default_factory=LlmSettings)
    scaffolding: ScaffoldingSettings = Field(default_factory=ScaffoldingSettings)

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
