from dataclasses import dataclass, field

from software_factory_poc.core.application.agents.common.agent_execution_mode import (
    AgentExecutionMode,
)
from software_factory_poc.core.application.ports import BrainPort, DocsPort, TrackerPort, VcsPort


@dataclass(frozen=True, kw_only=True)
class BaseAgentConfig:
    """Immutable configuration shared by all agents."""

    execution_mode: AgentExecutionMode = AgentExecutionMode.DETERMINISTIC
    priority_models: list[str] = field(default_factory=list)
    max_iterations: int = 5


@dataclass(frozen=True, kw_only=True)
class AgentPorts:
    """Groups the four infrastructure ports injected into every agent."""

    vcs: VcsPort
    tracker: TrackerPort
    docs: DocsPort
    brain: BrainPort
