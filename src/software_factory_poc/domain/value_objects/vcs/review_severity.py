from enum import Enum

class ReviewSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    SUGGESTION = "SUGGESTION"