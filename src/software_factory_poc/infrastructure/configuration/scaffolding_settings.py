from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ScaffoldingSettings(BaseSettings):
    """
    Settings for Scaffolding Agent.
    """
    work_dir: Path = Field(default=Path("/tmp/scaffolding_workspace"), description="Working directory", alias="WORK_DIR")
    enable_secure_mode: bool = Field(default=True, description="Enable secure mode", alias="ENABLE_SECURE_MODE")
    allowlisted_groups: list[str] = Field(default_factory=list, description="List of allowed groups/projects", alias="ALLOWLISTED_GROUPS")

    model_config = SettingsConfigDict(
        # env_prefix specified but aliases take precedence for specific fields if configured.
        # But we want to support both if possible? Or typically users just want the documented vars.
        # The prompt asked to read WORK_DIR.
        env_prefix="SCAFFOLDING_", # Keeping prefix for potentially future fields or non-aliased ones
        case_sensitive=True,
        extra="ignore"
    )
