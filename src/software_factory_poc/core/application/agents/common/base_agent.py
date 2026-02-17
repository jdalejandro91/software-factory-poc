from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from software_factory_poc.core.application.agents.common.agent_execution_mode import (
    AgentExecutionMode,
)
from software_factory_poc.core.application.ports.brain_port import BrainPort
from software_factory_poc.core.application.skills.registry import SkillRegistry
from software_factory_poc.core.domain.mission.entities.mission import Mission


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
        execution_mode: AgentExecutionMode = AgentExecutionMode.DETERMINISTIC,
    ):
        self._identity = identity
        self._brain = brain
        self._execution_mode = execution_mode

    @property
    def identity(self) -> AgentIdentity:
        return self._identity

    @property
    def execution_mode(self) -> AgentExecutionMode:
        return self._execution_mode

    async def run(self, mission: Mission, *, skills: SkillRegistry | None = None) -> Any:
        """
        Unified entrypoint.
        - DETERMINISTIC: child defines the deterministic contract (structured generation, strict parsing).
        - REACT_LOOP: BrainDriver runs tool loop, child provides tool executor.
        """
        if self._execution_mode == AgentExecutionMode.DETERMINISTIC:
            return await self._run_deterministic(mission)

        if skills is None:
            raise ValueError(f"{self._identity.name}: skills are required for REACT_LOOP mode")

        return await self._run_react_loop(mission, skills)

    @abstractmethod
    async def _run_deterministic(self, mission: Mission) -> Any:
        pass

    async def _run_react_loop(self, mission: Mission, skills: SkillRegistry) -> str:
        """
        Default ReAct loop wiring: delegate to BrainDriver and map tool calls to skills.
        """

        skills_by_name = skills.by_name()

        async def tool_executor(tool_name: str, tool_payload: dict[str, Any]) -> Any:
            skill = skills_by_name.get(tool_name)
            if skill is None:
                raise ValueError(f"{self._identity.name}: unknown tool '{tool_name}'")
            return await skill.execute(tool_payload)

        return await self._brain.run_agentic_loop(
            prompt=f"Mission: {mission.summary}",
            tools=skills.tools_payload(),
            tool_executor=tool_executor,
        )
