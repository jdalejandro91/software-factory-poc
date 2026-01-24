from abc import ABC, abstractmethod

class ReporterAgent(ABC):
    """
    Capability contract for Agents responsible for Reporting status back to users/trackers.
    """
    
    @abstractmethod
    def announce_start(self, task_id: str) -> None:
        """
        Announces the start of a task.
        """
        pass

    @abstractmethod
    def announce_completion(self, task_id: str, resource_url: str) -> None:
        """
        Announces the successful completion of a task, providing a resource link (e.g., MR URL).
        """
        pass
    
    @abstractmethod
    def announce_failure(self, task_id: str, error: Exception) -> None:
        """
        Announces a failure in the task execution.
        """
        pass

    @abstractmethod
    def announce_redundancy(self, task_id: str, resource_url: str) -> None:
        """
        Announces that the task is redundant (e.g., work already exists), providing the existing resource.
        """
        pass
