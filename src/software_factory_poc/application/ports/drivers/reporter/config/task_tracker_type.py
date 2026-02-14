try:
    from enum import StrEnum, auto
except ImportError:
    from enum import Enum, auto
    class StrEnum(str, Enum):
        pass


class TaskTrackerType(StrEnum):
    JIRA = auto()
    AZURE_DEVOPS = auto()
