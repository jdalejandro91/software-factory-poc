from abc import ABC, abstractmethod
from typing import Any, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class BrainPort(ABC):
    """Port for LLM interactions supporting the Dual Flow pattern.

    Implementations MUST raise:
        - ProviderError: on provider-level failures (rate limits, auth, timeouts).
        - InfraError: on infrastructure failures (network, serialization).

    Both live in ``core.application.ports.common.exceptions``.
    """

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        schema: type[T],
        priority_models: list[str],
    ) -> T:
        """[DETERMINISTIC] Request the LLM to return output validated against *schema*.

        Args:
            prompt: The fully-assembled prompt text.
            schema: A Pydantic model class used for structured output parsing.
            priority_models: Ordered list of ``provider:model`` identifiers to try.

        Returns:
            A validated instance of *schema*.

        Raises:
            ProviderError: When every provider in *priority_models* fails.
            InfraError: On unexpected infrastructure failures.
        """

    @abstractmethod
    async def generate_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        priority_models: list[str],
    ) -> dict[str, Any]:
        """[AGENTIC] Send messages and tool definitions; return the raw LLM response.

        The caller is responsible for executing tool calls and managing the ReAct loop.

        Args:
            messages: OpenAI-compatible message list.
            tools: OpenAI-compatible tool/function definitions.
            priority_models: Ordered list of ``provider:model`` identifiers to try.

        Returns:
            Raw response dict containing ``content`` and optionally ``tool_calls``.

        Raises:
            ProviderError: When every provider in *priority_models* fails.
            InfraError: On unexpected infrastructure failures.
        """
