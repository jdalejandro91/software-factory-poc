"""Skill that builds the scaffolding prompt and calls the LLM for structured code generation."""

import structlog

from software_factory_poc.core.application.exceptions import SkillExecutionError
from software_factory_poc.core.application.ports import BrainPort
from software_factory_poc.core.application.skills.scaffold.contracts.generate_scaffold_plan_input import (
    GenerateScaffoldPlanInput,
)
from software_factory_poc.core.application.skills.scaffold.contracts.scaffolder_contracts import (
    ScaffoldingResponseSchema,
)
from software_factory_poc.core.application.skills.scaffold.prompt_templates.scaffolding_prompt_builder import (
    ScaffoldingPromptBuilder,
)
from software_factory_poc.core.application.skills.skill import BaseSkill
from software_factory_poc.core.domain.shared.skill_type import SkillType

logger = structlog.get_logger()


class GenerateScaffoldPlanSkill(
    BaseSkill[GenerateScaffoldPlanInput, ScaffoldingResponseSchema],
):
    """Builds the scaffolding prompt and calls the LLM for structured code generation.

    Raises ``SkillExecutionError`` when the LLM returns zero files or fails.
    """

    @property
    def skill_type(self) -> SkillType:
        return SkillType.GENERATE_SCAFFOLD_PLAN

    def __init__(self, brain: BrainPort, prompt_builder: ScaffoldingPromptBuilder) -> None:
        self._brain = brain
        self._prompt_builder = prompt_builder

    async def execute(self, input_data: GenerateScaffoldPlanInput) -> ScaffoldingResponseSchema:
        ctx = {"skill": "generate_scaffold_plan", "mission_key": input_data.mission.key}
        try:
            return await self._generate_plan(input_data)
        except SkillExecutionError:
            raise
        except Exception as exc:
            raise SkillExecutionError(
                f"Scaffold plan generation failed: {exc}", context=ctx
            ) from exc

    async def _generate_plan(
        self, input_data: GenerateScaffoldPlanInput
    ) -> ScaffoldingResponseSchema:
        """Build prompts, invoke LLM, and validate the scaffold plan."""
        logger.info(
            "Building prompt", skill="generate_scaffold_plan", issue_key=input_data.mission.key
        )
        system_prompt, user_prompt = self._prompt_builder.build_prompt_from_mission(
            input_data.mission,
            input_data.arch_context,
        )
        scaffold_plan: ScaffoldingResponseSchema = await self._brain.generate_structured(
            prompt=user_prompt,
            schema=ScaffoldingResponseSchema,
            priority_models=input_data.priority_models,
            system_prompt=system_prompt,
        )
        if not scaffold_plan.files:
            ctx = {"skill": "generate_scaffold_plan", "mission_key": input_data.mission.key}
            raise SkillExecutionError("LLM returned 0 files — cannot proceed.", context=ctx)
        logger.info(
            "Scaffold plan generated",
            files_count=len(scaffold_plan.files),
            issue_key=input_data.mission.key,
        )
        return scaffold_plan
