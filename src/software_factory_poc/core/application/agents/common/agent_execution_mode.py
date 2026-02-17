from enum import Enum


class AgentExecutionMode(str, Enum):
    DETERMINISTIC = "DETERMINISTIC"
    REACT_LOOP = "REACT_LOOP"
