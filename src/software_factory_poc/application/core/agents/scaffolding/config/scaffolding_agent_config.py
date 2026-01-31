from pathlib import Path
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings

from software_factory_poc.application.core.agents.common.value_objects.model_id import ModelId
from software_factory_poc.application.core.agents.reporter.config.task_tracker_type import TaskTrackerType
from software_factory_poc.application.core.agents.research.config.research_provider_type import ResearchProviderType
from software_factory_poc.application.core.agents.vcs.config.vcs_provider_type import VcsProviderType


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
    
    # Keep original fields if they are still relevant, user didn't say to remove them but "Update this class".
    # Original: model_name, temperature, extra_params.
    # User instructions implied specific new fields. I'll keep the old ones as Optional/Default to be safe 
    # or replace them if the new ones cover them. 
    # 'model_name' might be covered by 'llm_model_priority' logic, but let's keep them to avoid breaking too much if used.
    model_name: Optional[str] = None
    temperature: float = 0.0
    extra_params: dict = Field(default_factory=dict)

    model_config = {
        "env_prefix": "SCAFFOLDING_",
        "case_sensitive": False
    }
