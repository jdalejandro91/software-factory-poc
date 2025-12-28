from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from software_factory_poc.config.allowlists_config import (
    DEFAULT_ALLOWLISTED_GITLAB_PROJECT_IDS,
    DEFAULT_ALLOWLISTED_TEMPLATE_IDS,
    DEFAULT_PROTECTED_BRANCHES,
)


class AppSettings(BaseSettings):
    # App Config
    app_name: str = "Software Factory PoC"
    log_level: str = "INFO"

    # Filesystem
    template_catalog_root: Path = Field(
        default=Path("src/software_factory_poc/templates/template_catalog")
    )
    runtime_data_dir: Path = Field(default=Path("runtime_data"))

    # Policies / Constraints
    default_target_base_branch: str = "main"
    
    allowlisted_template_ids: list[str] = Field(
        default_factory=lambda: DEFAULT_ALLOWLISTED_TEMPLATE_IDS
    )
    allowlisted_gitlab_project_ids: list[int] = Field(
        default_factory=lambda: DEFAULT_ALLOWLISTED_GITLAB_PROJECT_IDS
    )
    allowlisted_groups: list[str] = ["jdalejandro91-group"] # Default allowed namespace
    protected_branches: list[str] = Field(
        default_factory=lambda: DEFAULT_PROTECTED_BRANCHES
    )

    model_config = SettingsConfigDict(env_file=None, extra="ignore")
