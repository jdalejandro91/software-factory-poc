from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from software_factory_poc.core.application.agents.common.agent_config import AgentConfig
from software_factory_poc.core.application.skills.skill import BaseSkill
from software_factory_poc.core.domain.mission import Mission
from software_factory_poc.core.domain.shared.base_tool import BaseTool
from software_factory_poc.core.domain.shared.skill_type import SkillType
from software_factory_poc.core.domain.shared.tool_type import ToolType


@dataclass(frozen=True)
class AgentIdentity:
    name: str
    role: str
    goal: str


class BaseAgent(ABC):
    def __init__(
        self,
        identity: AgentIdentity,
        config: AgentConfig,
        tools: Mapping[ToolType, BaseTool],
        skills: Mapping[SkillType, BaseSkill[Any, Any]],
    ):
        self._identity = identity
        self._config = config
        self._tools = tools
        self._skills = skills
        self._execution_mode = config.execution_mode
        self._priority_models = config.priority_models

    @property
    def identity(self) -> AgentIdentity:
        return self._identity

    @abstractmethod
    async def _run_deterministic(self, mission: Mission) -> Any:
        pass
