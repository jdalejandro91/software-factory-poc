from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Protocol


class BaseSkill[T_Input, T_Output](ABC):
    """Abstract base for typed, domain-level skills.

    Subclasses define a concrete input/output contract enforced at compile time.
    """

    @abstractmethod
    async def execute(self, input_data: T_Input) -> T_Output:
        """Run the skill logic and return a typed result."""


@dataclass(frozen=True)
class SkillToolSpec:
    """Minimal tool spec compatible with ReAct-style tool calling."""

    name: str
    description: str
    input_schema: dict[str, Any]


class Skill(Protocol):
    def tool_spec(self) -> SkillToolSpec: ...

    async def execute(self, payload: dict[str, Any]) -> Any: ...


@dataclass(frozen=True)
class SkillAdapter:
    """Wraps an async callable into a Skill interface."""

    spec: SkillToolSpec
    handler: Callable[[dict[str, Any]], Awaitable[Any]]

    def tool_spec(self) -> SkillToolSpec:
        return self.spec

    async def execute(self, payload: dict[str, Any]) -> Any:
        return await self.handler(payload)
