from dataclasses import dataclass, field
from software_factory_poc.application.core.domain.configuration.task_status import TaskStatus

@dataclass
class Task:
    id: str
    status: TaskStatus = field(default=TaskStatus.TO_DO)

    def can_transition_to(self, new_status: TaskStatus) -> bool:
        """
        Validates if logic allows transition.
        For now, we allow almost any transition for robustness, 
        unless specific blocking logic is required.
        """
        # Example logic: cannot go back from DONE to TO_DO without reopening
        if self.status == TaskStatus.DONE and new_status != TaskStatus.DONE:
            # We might allow it for reopening
            return True
        return True
