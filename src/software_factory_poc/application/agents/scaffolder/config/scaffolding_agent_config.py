import json
from pathlib import Path
from typing import List, Optional, Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

from software_factory_poc.domain.value_objects.llm.model_id import ModelId
from software_factory_poc.domain.value_objects.research.research_provider_type import ResearchProviderType
from software_factory_poc.domain.value_objects.task.task_tracker_type import TaskTrackerType
from software_factory_poc.domain.value_objects.vcs.vcs_provider_type import VcsProviderType


class ScaffoldingAgentConfig(BaseSettings):
    """
    Configuration for ScaffoldingAgent.
    Holds runtime behaviors or feature flags.
    """
    vcs_provider: VcsProviderType = Field(..., description="VCS Provider to use")
    tracker_provider: TaskTrackerType = Field(..., description="Task Tracker Provider to use")
    research_provider: ResearchProviderType = Field(..., description="Knowledge Provider to use")
    llm_model_priority: List[ModelId] = Field(default_factory=list, description="Priority list of LLM models")
    project_allowlist: List[str] = Field(default_factory=list, description="List of allowed projects")
    enable_secure_mode: bool = Field(default=True, description="Enable secure mode")
    work_dir: Path = Field(..., description="Working directory")
    default_target_branch: str = Field(default="main", description="Target branch for Merge Requests")
    architecture_page_id: Optional[str] = Field(default=None, description="Confluence Page ID for Architecture")

    # Original fields kept for compatibility
    model_name: Optional[str] = None
    temperature: float = 0.0
    extra_params: dict = Field(default_factory=dict)

    @field_validator("project_allowlist", mode="before")
    @classmethod
    def parse_allowlist(cls, v: Any) -> List[str]:
        """
        Robustly parses allowlist from various formats:
        - List[str]: ['group1'] (Already parsed)
        - JSON string: '["group1", "group2"]'
        - CSV string: 'group1,group2'
        """
        if isinstance(v, list):
            return v

        if isinstance(v, str):
            v = v.strip()
            if not v:
                return []

            # 1. Try JSON parsing (handles '["item"]' formats common in Docker envs)
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return [str(item) for item in parsed]
            except json.JSONDecodeError:
                pass

            # 2. Fallback to CSV splitting
            # Remove potential quotes if they were part of the string but not valid JSON
            clean_str = v.replace("'", "").replace('"', "")
            return [g.strip() for g in clean_str.split(",") if g.strip()]

        return []

    model_config = {
        "env_prefix": "SCAFFOLDING_",
        "case_sensitive": False
    }