from dataclasses import dataclass

from software_factory_poc.core.application.agents.common.agent_structures import BaseAgentConfig


@dataclass(frozen=True, kw_only=True)
class ScaffolderAgentConfig(BaseAgentConfig):
    """DI configuration specific to the Scaffolder Agent.

    Inherits ``execution_mode``, ``priority_models``, and ``max_iterations``
    from ``BaseAgentConfig``.  Extend with scaffolder-specific knobs as needed.
    """
