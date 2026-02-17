import json
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

from software_factory_poc.core.application.agents.common.agent_execution_mode import (
    AgentExecutionMode,
)
from software_factory_poc.core.domain.value_objects.llm.model_id import ModelId
from software_factory_poc.core.domain.value_objects.research.research_provider_type import (
    ResearchProviderType,
)
from software_factory_poc.core.domain.value_objects.task.task_tracker_type import TaskTrackerType
from software_factory_poc.core.domain.value_objects.vcs.vcs_provider_type import VcsProviderType


class ScaffolderAgentConfig(BaseSettings):
    execution_mode: AgentExecutionMode = Field(
        default=AgentExecutionMode.DETERMINISTIC,
        description="Per-agent switch: DETERMINISTIC (Golden Path) vs REACT_LOOP",
    )

    vcs_provider: VcsProviderType = Field(..., description="VCS Provider to use")
    tracker_provider: TaskTrackerType = Field(..., description="Task Tracker Provider to use")
    research_provider: ResearchProviderType = Field(..., description="Knowledge Provider to use")
    llm_model_priority: list[ModelId] = Field(default_factory=list, description="Priority list of LLM models")
    project_allowlist: list[str] = Field(default_factory=list, description="List of allowed projects")
    enable_secure_mode: bool = Field(default=True, description="Enable secure mode")
    work_dir: Path = Field(..., description="Working directory")
    default_target_branch: str = Field(default="main", description="Target branch for Merge Requests")
    architecture_page_id: str | None = Field(default=None, description="Confluence Page ID for Architecture")

    model_name: str | None = None
    temperature: float = 0.0
    extra_params: dict = Field(default_factory=dict)

    @field_validator("project_allowlist", mode="before")
    @classmethod
    def parse_allowlist(cls, v: Any) -> list[str]:
        if isinstance(v, list):
            return v

        if isinstance(v, str):
            v = v.strip()
            if not v:
                return []

            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return [str(item) for item in parsed]
            except json.JSONDecodeError:
                pass

            clean_str = v.replace("'", "").replace('"', "")
            return [g.strip() for g in clean_str.split(",") if g.strip()]

        return []
