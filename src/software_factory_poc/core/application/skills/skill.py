from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class SkillToolSpec:
    """
    Minimal tool spec compatible with ReAct-style tool calling.
    You can map this to whatever your BrainDriver expects as 'tools: List[Dict]'.
    """

    name: str
    description: str
    input_schema: dict[str, Any]


class Skill(Protocol):
    def tool_spec(self) -> SkillToolSpec: ...

    async def execute(self, payload: dict[str, Any]) -> Any: ...


@dataclass(frozen=True)
class SkillAdapter:
    """
    Wraps an async callable into a Skill interface.
    """

    spec: SkillToolSpec
    handler: Callable[[dict[str, Any]], Awaitable[Any]]

    def tool_spec(self) -> SkillToolSpec:
        return self.spec

    async def execute(self, payload: dict[str, Any]) -> Any:
        return await self.handler(payload)
