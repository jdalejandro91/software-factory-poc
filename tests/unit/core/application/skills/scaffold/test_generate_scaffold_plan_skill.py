"""Unit tests — GenerateScaffoldPlanSkill (zero I/O, AsyncMock for Ports)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from software_factory_poc.core.application.agents.scaffolder.contracts.scaffolder_contracts import (
    FileSchemaDTO,
    ScaffoldingResponseSchema,
)
from software_factory_poc.core.application.skills.scaffold.generate_scaffold_plan_skill import (
    GenerateScaffoldPlanInput,
    GenerateScaffoldPlanSkill,
)
from software_factory_poc.core.domain.mission import Mission, TaskDescription


def _make_mission() -> Mission:
    return Mission(
        id="1",
        key="PROJ-10",
        summary="Create API service",
        status="To Do",
        project_key="PROJ",
        issue_type="Task",
        description=TaskDescription(raw_content="Create API", config={}),
    )


def _make_plan(file_count: int = 2) -> ScaffoldingResponseSchema:
    files = [
        FileSchemaDTO(path=f"src/file_{i}.py", content=f"# file {i}", is_new=True)
        for i in range(file_count)
    ]
    return ScaffoldingResponseSchema(
        branch_name="feature/proj-10",
        commit_message="feat: scaffold",
        files=files,
    )


class TestGenerateScaffoldPlanSkill:
    async def test_returns_scaffold_plan_from_brain(self) -> None:
        brain = AsyncMock()
        prompt_builder = MagicMock()
        prompt_builder.build_prompt_from_mission.return_value = "full prompt"
        plan = _make_plan()
        brain.generate_structured.return_value = plan

        skill = GenerateScaffoldPlanSkill(brain=brain, prompt_builder=prompt_builder)
        mission = _make_mission()

        result = await skill.execute(
            GenerateScaffoldPlanInput(
                mission=mission,
                arch_context="arch",
                priority_models=["openai:gpt-4o"],
            )
        )

        assert result is plan
        assert len(result.files) == 2
        prompt_builder.build_prompt_from_mission.assert_called_once_with(mission, "arch")
        brain.generate_structured.assert_awaited_once_with(
            prompt="full prompt",
            schema=ScaffoldingResponseSchema,
            priority_models=["openai:gpt-4o"],
        )

    async def test_raises_value_error_when_zero_files(self) -> None:
        brain = AsyncMock()
        prompt_builder = MagicMock()
        prompt_builder.build_prompt_from_mission.return_value = "prompt"
        brain.generate_structured.return_value = _make_plan(file_count=0)

        skill = GenerateScaffoldPlanSkill(brain=brain, prompt_builder=prompt_builder)

        with pytest.raises(ValueError, match="0 archivos"):
            await skill.execute(
                GenerateScaffoldPlanInput(
                    mission=_make_mission(),
                    arch_context="arch",
                    priority_models=["openai:gpt-4o"],
                )
            )
