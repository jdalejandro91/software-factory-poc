from enum import StrEnum


class AgentExecutionMode(StrEnum):
    """Defines how an agent executes its mission.

    * DETERMINISTIC: step-by-step pipeline with no LLM autonomy.
    * REACT_LOOP: Think -> Act -> Observe cycle driven by the LLM.
    """

    DETERMINISTIC = "DETERMINISTIC"
    REACT_LOOP = "REACT_LOOP"
