from dataclasses import dataclass
from pathlib import Path
from software_factory_poc.infrastructure.configuration.tool_settings import ToolSettings
from software_factory_poc.infrastructure.configuration.llm_settings import LlmSettings


class Settings(ToolSettings, LlmSettings):
    """
    Combines all settings.
    Inherits from ToolSettings and LlmSettings.
    """
    app_name: str = "Software Factory PoC"
    runtime_data_dir: Path = Path("./runtime_data")
    
# For backward compatibility during refactor, and for DI containers
GlobalSettings = Settings
