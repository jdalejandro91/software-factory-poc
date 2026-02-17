from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any


class BrainPort(ABC):
    @abstractmethod
    async def generate_structured(self, prompt: str, schema_cls: Any) -> Any:
        """[DETERMINISTIC] Requests the LLM for a strict output validated against schema_cls."""
        pass

    @abstractmethod
    async def run_agentic_loop(self, prompt: str, tools: list[dict], tool_executor: Callable) -> str:
        """[AGENTIC] Runs a ReAct cycle delegating executions to the tool_executor."""
        pass
