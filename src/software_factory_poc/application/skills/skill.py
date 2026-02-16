from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, Protocol


@dataclass(frozen=True)
class SkillToolSpec:
    """
    Minimal tool spec compatible with ReAct-style tool calling.
    You can map this to whatever your BrainDriver expects as 'tools: List[Dict]'.
    """
    name: str
    description: str
    input_schema: Dict[str, Any]


class Skill(Protocol):
    def tool_spec(self) -> SkillToolSpec:
        ...

    async def execute(self, payload: Dict[str, Any]) -> Any:
        ...


@dataclass(frozen=True)
class SkillAdapter:
    """
    Wraps an async callable into a Skill interface.
    """
    spec: SkillToolSpec
    handler: Callable[[Dict[str, Any]], Awaitable[Any]]

    def tool_spec(self) -> SkillToolSpec:
        return self.spec

    async def execute(self, payload: Dict[str, Any]) -> Any:
        return await self.handler(payload)
