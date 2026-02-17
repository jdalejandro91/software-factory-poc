from collections.abc import Callable
from typing import Any

from software_factory_poc.core.application.ports.brain_port import BrainPort


class LiteLlmBrainAdapter(BrainPort):
    """Implements BrainPort via litellm.completion.

    TODO: Wire litellm.completion + structured output parsing.
    """

    async def generate_structured(self, prompt: str, schema_cls: Any) -> Any:
        raise NotImplementedError("LiteLLM integration pending")

    async def run_agentic_loop(self, prompt: str, tools: list[dict], tool_executor: Callable) -> str:
        raise NotImplementedError("LiteLLM agentic loop pending")
