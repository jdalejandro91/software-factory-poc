from software_factory_poc.configuration.application.app_settings import AppSettings
from software_factory_poc.configuration.llms.llm_settings import LlmSettings
from software_factory_poc.configuration.tools.tool_settings import ToolSettings


class GlobalSettings(AppSettings, LlmSettings, ToolSettings):
    """
    Master configuration class that aggregates all setting modules.
    Usage:
        settings = GlobalSettings()
    """
    pass

# For backward compatibility during refactor, and for DI containers
Settings = GlobalSettings
