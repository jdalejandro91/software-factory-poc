from dataclasses import dataclass, field
from pathlib import Path

from software_factory_poc.application.core.domain.configuration.knowledge_provider_type import (
    KnowledgeProviderType,
)
from software_factory_poc.application.core.domain.value_objects.model_id import ModelId
from software_factory_poc.application.core.domain.configuration.task_tracker_type import (
    TaskTrackerType,
)
from software_factory_poc.application.core.domain.configuration.vcs_provider_type import (
    VcsProviderType,
)


@dataclass(frozen=True)
class ScaffoldingAgentConfig:
    vcs_provider: VcsProviderType
    tracker_provider: TaskTrackerType
    knowledge_provider: KnowledgeProviderType
    llm_model_priority: list[ModelId]
    work_dir: Path
    architecture_page_id: str
    enable_secure_mode: bool = True
