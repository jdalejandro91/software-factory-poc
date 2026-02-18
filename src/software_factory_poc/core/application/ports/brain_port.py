from abc import ABC, abstractmethod
from typing import Any, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class BrainPort(ABC):
    """Abstract cognitive engine port for LLM interactions.

    This is NOT a tool — it is the intrinsic cognitive motor of every agent.
    It supports the Dual Flow pattern:

    * **Deterministic flow**: ``generate_structured`` returns validated Pydantic models.
    * **ReAct loop flow**: ``generate_with_tools`` drives think-act-observe cycles.

    Implementations MUST raise:
        - ``ProviderError``: on provider-level failures (rate limits, auth, timeouts).
    """

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        schema: type[T],
        priority_models: list[str],
        system_prompt: str = "",
    ) -> T:
        """Request the LLM to return output validated against *schema*."""

    @abstractmethod
    async def generate_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        priority_models: list[str],
    ) -> dict[str, Any]:
        """Send messages and tool definitions; return the raw LLM response."""
