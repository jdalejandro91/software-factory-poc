from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from software_factory_poc.core.application.skills.skill import Skill


@dataclass(frozen=True)
class SkillRegistry:
    skills: list[Skill]

    def tools_payload(self) -> list[dict[str, Any]]:
        """
        Converts skills to the primitive List[Dict] shape expected by BrainDriver.run_agentic_loop.
        """
        tools: list[dict[str, Any]] = []
        for s in self.skills:
            spec = s.tool_spec()
            tools.append(
                {
                    "name": spec.name,
                    "description": spec.description,
                    "input_schema": spec.input_schema,
                }
            )
        return tools

    def by_name(self) -> dict[str, Skill]:
        return {s.tool_spec().name: s for s in self.skills}
