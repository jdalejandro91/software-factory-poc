from abc import abstractmethod
from typing import Any, TypeVar

from pydantic import BaseModel

from software_factory_poc.core.domain.shared.base_tool import BaseTool
from software_factory_poc.core.domain.shared.tool_type import ToolType

T = TypeVar("T", bound=BaseModel)


class BrainTool(BaseTool):
    """Abstract tool contract for LLM interactions supporting the Dual Flow pattern.

    Implementations MUST raise:
        - ProviderError: on provider-level failures (rate limits, auth, timeouts).
        - InfraError: on infrastructure failures (network, serialization).

    Both live in ``core.application.tools.common.exceptions``.
    """

    @property
    def tool_type(self) -> ToolType:
        return ToolType.BRAIN

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        schema: type[T],
        priority_models: list[str],
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
