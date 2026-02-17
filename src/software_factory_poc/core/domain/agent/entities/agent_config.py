from dataclasses import dataclass, field

from software_factory_poc.core.domain.agent.value_objects.agent_execution_mode import (
    AgentExecutionMode,
)


@dataclass(frozen=True, kw_only=True)
class AgentConfig:
    """Immutable configuration shared by all agents."""

    execution_mode: AgentExecutionMode = AgentExecutionMode.DETERMINISTIC
    priority_models: list[str] = field(default_factory=list)
    max_iterations: int = 5


@dataclass(frozen=True, kw_only=True)
class ScaffolderAgentConfig(AgentConfig):
    """DI configuration specific to the Scaffolder Agent."""


@dataclass(frozen=True, kw_only=True)
class CodeReviewerAgentConfig(AgentConfig):
    """DI configuration specific to the Code Reviewer Agent."""
