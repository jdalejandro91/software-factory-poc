from dataclasses import dataclass

from software_factory_poc.application.drivers.brain.brain_driver import BrainDriver

@dataclass
class BaseAgent:
    """
    Base definition for a Domain Agent, establishing its identity and purpose.
    """
    name: str
    role: str
    goal: str
    brain: BrainDriver
