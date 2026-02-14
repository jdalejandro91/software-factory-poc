from abc import ABC, abstractmethod
from typing import Any

from software_factory_poc.application.ports.drivers.common.config.task_status import TaskStatus
from software_factory_poc.domain.entities.task import Task, TaskDescription


class TaskTrackerGateway(ABC):
    @abstractmethod
    def add_comment(self, task_id: str, body: Any) -> None:
        """Adds a comment to the task."""
        pass

    @abstractmethod
    def transition_status(self, task_id: str, status: TaskStatus) -> None:
        """Transitions the task to a new status."""
        pass

    @abstractmethod
    def update_task_description(self, task_id: str, description: TaskDescription) -> None:
        """
        Updates the text description of the task using Domain Object.
        Argument is Any to avoid circular imports in Port if strictly separate,
        but ideally would be TaskDescription.
        """
        pass

    @abstractmethod
    def append_issue_description(self, task_id: str, content: str) -> None:
        """Appends content to the task description without overwriting."""
        pass

    @abstractmethod
    def get_task(self, task_id: str) -> Task:
        """Retrieves the Task domain entity."""
        pass
