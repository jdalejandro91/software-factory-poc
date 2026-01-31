from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ScaffoldingSettings(BaseSettings):
    """
    Settings for Scaffolding Agent.
    """
    work_dir: Path = Field(default=Path("/tmp/scaffolding_workspace"), description="Working directory", alias="WORK_DIR")
    enable_secure_mode: bool = Field(default=True, description="Enable secure mode", alias="ENABLE_SECURE_MODE")
    allowlisted_groups: list[str] = Field(default_factory=list, description="List of allowed groups/projects", alias="ALLOWLISTED_GROUPS")

    @field_validator("allowlisted_groups", mode="before")
    @classmethod
    def parse_allowlist_robust(cls, v: Any) -> list[str]:
        """
        Allows the environment variable to be a JSON (["group"])
        Or a comma-separated string (group1,group2), avoiding parsing errors.
        """
        if isinstance(v, str):
            if not v.strip():
                return []
            clean_str = v.replace("[", "").replace("]", "").replace('"', '').replace("'", "")
            return [g.strip() for g in clean_str.split(",") if g.strip()]
        return v
    # ------------------------------

    model_config = SettingsConfigDict(
        env_prefix="SCAFFOLDING_",
        case_sensitive=True,
        extra="ignore"
    )