from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from software_factory_poc.core.application.agents.common.agent_execution_mode import (
    AgentExecutionMode,
)
from software_factory_poc.core.application.ports import BrainPort
from software_factory_poc.core.domain.mission import Mission


@dataclass(frozen=True)
class AgentIdentity:
    name: str
    role: str
    goal: str


class BaseAgent(ABC):
    def __init__(
        self,
        identity: AgentIdentity,
        brain: BrainPort,
        priority_models: list[str],
        execution_mode: AgentExecutionMode = AgentExecutionMode.DETERMINISTIC,
    ):
        self._identity = identity
        self._brain = brain
        self._priority_models = priority_models
        self._execution_mode = execution_mode

    @property
    def identity(self) -> AgentIdentity:
        return self._identity

    @property
    def execution_mode(self) -> AgentExecutionMode:
        return self._execution_mode

    @abstractmethod
    async def _run_deterministic(self, mission: Mission) -> Any:
        pass
