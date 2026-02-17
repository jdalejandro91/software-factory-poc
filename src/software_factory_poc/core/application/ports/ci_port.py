from abc import ABC, abstractmethod
from typing import Any


class CiPort(ABC):
    @abstractmethod
    async def trigger_pipeline(self, project_id: str, ref: str, variables: dict[str, Any] | None = None) -> str:
        """Triggers a CI pipeline. Returns the pipeline ID."""
        pass

    @abstractmethod
    async def get_pipeline_status(self, project_id: str, pipeline_id: str) -> str:
        """Returns the current status of a pipeline."""
        pass
