from abc import ABC, abstractmethod

from software_factory_poc.core.domain.mission import Mission


class BaseWorkflow(ABC):
    """Abstract base for all deterministic workflow pipelines."""

    @abstractmethod
    async def execute(self, mission: Mission) -> None:
        """Run the full workflow pipeline for the given mission."""
