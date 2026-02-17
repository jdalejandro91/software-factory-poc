from pathlib import Path

from software_factory_poc.infrastructure.tools.llm.config.llm_settings import LlmSettings


class Settings(LlmSettings):
    """
    Application-level settings.
    Inherits LLM keys from LlmSettings. Tool-specific config lives
    in isolated settings classes (GitLabSettings, JiraSettings, etc.).
    """

    app_name: str = "Software Factory PoC"
    runtime_data_dir: Path = Path("./runtime_data")
