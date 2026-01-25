from abc import ABC, abstractmethod
from typing import Any
from software_factory_poc.application.core.agents.common.config.task_status import TaskStatus

class TaskTrackerGateway(ABC):
    @abstractmethod
    def add_comment(self, task_id: str, body: Any) -> None:
        """Adds a comment to the task."""
        pass

    @abstractmethod
    def transition_status(self, task_id: str, status: TaskStatus) -> None:
        """Transitions the task to a new status."""
        pass
