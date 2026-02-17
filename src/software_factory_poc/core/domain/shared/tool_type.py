from enum import StrEnum, auto


class ToolType(StrEnum):
    """Classifies every external tool the system can interact with."""

    VCS = auto()
    TRACKER = auto()
    DOCS = auto()
    BRAIN = auto()
