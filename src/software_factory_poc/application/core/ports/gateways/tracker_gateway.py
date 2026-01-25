from abc import ABC, abstractmethod

from software_factory_poc.application.core.ports.gateways.dtos import TaskDTO


class TrackerGateway(ABC):
    @abstractmethod
    def get_task(self, id: str) -> TaskDTO:
        """
        Retrieves a task by its ID.
        """
        raise NotImplementedError

    @abstractmethod
    def comment_on_task(self, id: str, body: str) -> None:
        """
        Adds a comment to a task.
        """
        raise NotImplementedError

    @abstractmethod
    def transition_task(self, id: str, status: str) -> None:
        """
        Transitions a task to a new status.
        """
        raise NotImplementedError
