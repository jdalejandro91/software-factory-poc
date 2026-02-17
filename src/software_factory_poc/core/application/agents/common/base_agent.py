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
        """Default ReAct loop: delegate tool-call dispatch to the agent while the
        LLM interaction goes through ``BrainPort.generate_with_tools``."""

        skills_by_name = skills.by_name()
        messages: list[dict[str, Any]] = [
            {"role": "user", "content": f"Mission: {mission.summary}"},
        ]
        tools_payload = skills.tools_payload()

        while True:
            response = await self._brain.generate_with_tools(
                messages=messages,
                tools=tools_payload,
                priority_models=self._priority_models,
            )

            tool_calls: list[dict[str, Any]] = response.get("tool_calls", [])

            if not tool_calls:
                return str(response.get("content", ""))

            messages.append(
                {
                    "role": "assistant",
                    "content": response.get("content", ""),
                    "tool_calls": tool_calls,
                },
            )

            for tool_call in tool_calls:
                fn = tool_call.get("function", {})
                tool_name: str = fn.get("name", "")
                tool_args: dict[str, Any] = fn.get("arguments", {})

                skill = skills_by_name.get(tool_name)
                if skill is None:
                    raise ValueError(f"{self._identity.name}: unknown tool '{tool_name}'")

                result = await skill.execute(tool_args)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.get("id", ""),
                        "content": str(result),
                    },
                )
