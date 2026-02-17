from abc import ABC, abstractmethod
from typing import Any


class RunStorePort(ABC):
    @abstractmethod
    async def save_run_step(self, run_id: str, step_name: str, data: dict[str, Any]) -> None:
        """Persists a single step of an agent run."""
        pass

    @abstractmethod
    async def get_run_step(self, run_id: str, step_name: str) -> dict[str, Any] | None:
        """Retrieves a persisted run step."""
        pass
