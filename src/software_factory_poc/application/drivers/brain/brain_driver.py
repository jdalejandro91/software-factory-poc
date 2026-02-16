from abc import ABC, abstractmethod
from typing import Any, Callable, List, Dict

class BrainDriver(ABC):
    @abstractmethod
    async def generate_structured(self, prompt: str, schema_cls: Any) -> Any:
        """[DETERMINISTIC] Requests the LLM for a strict output validated against schema_cls."""
        pass

    @abstractmethod
    async def run_agentic_loop(self, prompt: str, tools: List[Dict], tool_executor: Callable) -> str:
        """[AGENTIC] Runs a ReAct cycle delegating executions to the tool_executor."""
        pass