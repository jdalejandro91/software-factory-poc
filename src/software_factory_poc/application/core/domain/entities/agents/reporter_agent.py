from abc import ABC, abstractmethod
from typing import Any

class ReporterAgent(ABC):
    """
    Domain Entity/Service responsible for task status communication.
    """

    @abstractmethod
    def announce_start(self, task_id: str) -> None:
        """
        Announces that the task has started.
        """
        pass

    @abstractmethod
    def announce_success(self, task_id: str, result_link: str) -> None:
        """
        Announces successful completion of the task.
        """
        pass

    @abstractmethod
    def announce_failure(self, task_id: str, error: Exception) -> None:
        """
        Announces task failure with error details.
        """
        pass
