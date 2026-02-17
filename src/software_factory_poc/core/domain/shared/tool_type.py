from enum import StrEnum, auto


class ToolType(StrEnum):
    """Classifies every *peripheral* tool the system can interact with.

    Note: The LLM (Brain) is NOT a tool — it is the cognitive engine
    of the agent and lives as an independent port (``BrainPort``).
    """

    VCS = auto()
    TRACKER = auto()
    DOCS = auto()
