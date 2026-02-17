import logging
from dataclasses import dataclass

from software_factory_poc.core.application.agents.scaffolder.contracts.scaffolder_contracts import (
    ScaffoldingResponseSchema,
)
from software_factory_poc.core.application.agents.scaffolder.prompt_templates.scaffolding_prompt_builder import (
    ScaffoldingPromptBuilder,
)
from software_factory_poc.core.application.ports import BrainPort
from software_factory_poc.core.application.skills.skill import BaseSkill
from software_factory_poc.core.domain.mission import Mission

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GenerateScaffoldPlanInput:
    """Input contract for scaffold plan generation."""

    mission: Mission
    arch_context: str
    priority_models: list[str]


class GenerateScaffoldPlanSkill(
    BaseSkill[GenerateScaffoldPlanInput, ScaffoldingResponseSchema],
):
    """Builds the scaffolding prompt and calls the LLM for structured code generation.

    Raises ``ValueError`` when the LLM returns zero files.
    """

    def __init__(self, brain: BrainPort, prompt_builder: ScaffoldingPromptBuilder) -> None:
        self._brain = brain
        self._prompt_builder = prompt_builder

    async def execute(self, input_data: GenerateScaffoldPlanInput) -> ScaffoldingResponseSchema:
        logger.info("[GenerateScaffoldPlan] Building prompt for %s", input_data.mission.key)

        prompt = self._prompt_builder.build_prompt_from_mission(
            input_data.mission,
            input_data.arch_context,
        )

        scaffold_plan: ScaffoldingResponseSchema = await self._brain.generate_structured(
            prompt=prompt,
            schema=ScaffoldingResponseSchema,
            priority_models=input_data.priority_models,
        )

        if not scaffold_plan.files:
            raise ValueError("El LLM genero 0 archivos. No se puede continuar.")

        logger.info(
            "[GenerateScaffoldPlan] Generated %d files for %s",
            len(scaffold_plan.files),
            input_data.mission.key,
        )
        return scaffold_plan
