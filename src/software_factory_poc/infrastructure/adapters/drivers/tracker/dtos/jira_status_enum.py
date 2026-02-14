try:
    from enum import StrEnum
except ImportError:
    from enum import Enum
    class StrEnum(str, Enum):
        pass

class JiraStatus(StrEnum):
    TO_DO = "Por hacer"
    IN_PROGRESS = "En curso"
    IN_REVIEW = "In Review" # Or "En revisión" depending on checks
    DONE = "Listo"
