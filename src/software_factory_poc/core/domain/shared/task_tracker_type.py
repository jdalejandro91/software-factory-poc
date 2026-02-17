from enum import StrEnum, auto


class TaskTrackerType(StrEnum):
    JIRA = auto()
    AZURE_DEVOPS = auto()
