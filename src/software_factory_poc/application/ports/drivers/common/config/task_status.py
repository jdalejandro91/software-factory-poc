try:
    from enum import StrEnum
except ImportError:
    from enum import Enum
    class StrEnum(str, Enum):
        pass

class TaskStatus(StrEnum):
    TO_DO = "To Do"
    IN_PROGRESS = "In Progress" 
    IN_REVIEW = "In Review"
    DONE = "Done"
    # Add other statuses as needed by the standard workflow
