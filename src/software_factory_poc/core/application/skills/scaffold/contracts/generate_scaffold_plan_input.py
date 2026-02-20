"""Input contract for scaffold plan generation."""

from dataclasses import dataclass

from software_factory_poc.core.domain.mission import Mission


@dataclass(frozen=True)
class GenerateScaffoldPlanInput:
    """Input contract for scaffold plan generation."""

    mission: Mission
    arch_context: str
    priority_models: list[str]
