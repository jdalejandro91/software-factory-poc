import json
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ScaffoldingSettings(BaseSettings):
    """Settings for Scaffolding Agent."""

    work_dir: Path = Field(
        default=Path("/tmp/scaffolding_workspace"),
        description="Working directory",
        alias="WORK_DIR",
    )
    enable_secure_mode: bool = Field(
        default=True, description="Enable secure mode", alias="ENABLE_SECURE_MODE"
    )
    allowlisted_groups: list[str] = Field(
        default_factory=list,
        description="List of allowed groups/projects",
        alias="ALLOWLISTED_GROUPS",
    )

    model_config = SettingsConfigDict(
        env_prefix="SCAFFOLDING_", case_sensitive=True, extra="ignore"
    )

    @field_validator("allowlisted_groups", mode="before")
    @classmethod
    def parse_groups(cls, value: object) -> list[str]:
        """Parse comma-separated string or JSON array into a list."""
        if isinstance(value, str):
            return cls._parse_string_value(value)
        if isinstance(value, list):
            return [str(v) for v in value]
        return []

    @classmethod
    def _parse_string_value(cls, value: str) -> list[str]:
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else []
        except json.JSONDecodeError:
            if not value.strip():
                return []
            return [v.strip() for v in value.split(",")]