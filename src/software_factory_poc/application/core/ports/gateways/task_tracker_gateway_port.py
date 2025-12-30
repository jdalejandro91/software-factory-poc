from abc import ABC, abstractmethod
from typing import Any
from software_factory_poc.application.core.domain.configuration.task_status import TaskStatus

class TaskTrackerGatewayPort(ABC):
    @abstractmethod
    def add_comment(self, task_id: str, body: str) -> None:
        """Adds a comment to the task."""
        pass

    @abstractmethod
    def transition_status(self, task_id: str, status: TaskStatus) -> None:
        """Transitions the task to a new status."""
        pass
