from dataclasses import dataclass, field
from typing import Optional

@dataclass
class ScaffoldingAgentConfig:
    """
    Configuration for ScaffoldingAgent.
    Holds runtime behaviors or feature flags.
    """
    model_name: Optional[str] = None
    temperature: float = 0.0
    extra_params: dict = field(default_factory=dict)
