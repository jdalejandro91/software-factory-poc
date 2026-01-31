from dataclasses import dataclass

@dataclass
class BaseAgent:
    """
    Base definition for a Domain Agent, establishing its identity and purpose.
    """
    name: str
    role: str
    goal: str
