from unittest.mock import AsyncMock, MagicMock

import pytest

from software_factory_poc.core.application.agents.common.agent_config import (
    ScaffolderAgentConfig,
)
from software_factory_poc.core.application.agents.scaffolder.scaffolder_agent import ScaffolderAgent
from software_factory_poc.core.application.skills.scaffold.contracts.scaffolder_contracts import (
    FileSchemaDTO,
    ScaffoldingResponseSchema,
)
from software_factory_poc.core.application.skills.scaffold.generate_scaffold_plan_skill import (
    GenerateScaffoldPlanSkill,
)
from software_factory_poc.core.application.workflows.scaffold.scaffolding_deterministic_workflow import (
    ScaffoldingDeterministicWorkflow,
)
from software_factory_poc.core.domain.mission import Mission, TaskDescription
from software_factory_poc.core.domain.shared.skill_type import SkillType
from software_factory_poc.core.domain.shared.tool_type import ToolType


@pytest.mark.asyncio
async def test_scaffolder_agent_flow():
    """
    Integration test for ScaffolderAgent.run.
    Verifies the orchestration from Idempotency -> Context -> Plan -> Delivery -> Report.
    """

    # 1. Setup Mocks for Tools
    mock_vcs = AsyncMock()
    mock_vcs.validate_branch_existence.return_value = False
    mock_vcs.commit_changes.return_value = "commit-hash-123"
    mock_vcs.create_merge_request.return_value = "https://gitlab.com/mr/1"

    mock_tracker = AsyncMock()

    mock_docs = AsyncMock()
    mock_docs.get_architecture_context.return_value = "Architecture Guidelines..."

    mock_brain = AsyncMock()
    mock_brain.generate_structured.return_value = ScaffoldingResponseSchema(
        files=[FileSchemaDTO(path="README.md", content="# New Project", is_new=True)],
        commit_message="feat: init project",
        branch_name="feature/poc50-user-service",
    )

    mock_prompt_builder = MagicMock()
    mock_prompt_builder.build_prompt_from_mission.return_value = "Prompt..."

    # 2. Setup Mission
    description = TaskDescription(
        raw_content="...",
        config={
            "parameters": {"service_name": "user-service"},
            "target": {"default_branch": "main", "gitlab_project_id": "100"},
        },
    )
    mission = Mission(
        id="101",
        key="POC-50",
        summary="Build User Service",
        status="To Do",
        project_key="POC",
        issue_type="Task",
        description=description,
    )

    # 3. Build tools, skills, and workflow
    tools = {
        ToolType.VCS: mock_vcs,
        ToolType.TRACKER: mock_tracker,
        ToolType.DOCS: mock_docs,
    }
    generate_plan_skill = GenerateScaffoldPlanSkill(
        brain=mock_brain, prompt_builder=mock_prompt_builder
    )
    skills = {
        SkillType.GENERATE_SCAFFOLD_PLAN: generate_plan_skill,
    }
    priority_models = ["openai:gpt-4o"]
    deterministic_workflow = ScaffoldingDeterministicWorkflow(
        vcs=mock_vcs,
        tracker=mock_tracker,
        docs=mock_docs,
        generate_plan=generate_plan_skill,
        priority_models=priority_models,
    )

    # 4. Instantiate Agent
    agent = ScaffolderAgent(
        config=ScaffolderAgentConfig(priority_models=priority_models),
        brain=mock_brain,
        tools=tools,
        skills=skills,
        deterministic_workflow=deterministic_workflow,
    )

    # 5. Execute Flow
    await agent.run(mission)

    # 6. Assertions

    # Tracker: Start comment + success comment + description update + status
    assert mock_tracker.add_comment.call_count >= 2
    mock_tracker.update_task_description.assert_called_once()
    mock_tracker.update_status.assert_called_with("POC-50", "In Review")

    # VCS: Branch validation -> Creation -> Commit -> MR
    mock_vcs.validate_branch_existence.assert_called()
    mock_vcs.create_branch.assert_called_with("feature/poc-50-user-service", ref="main")
    mock_vcs.commit_changes.assert_called()
    mock_vcs.create_merge_request.assert_called()

    # Docs: Architecture context
    mock_docs.get_architecture_context.assert_called()

    # Brain: Generate (via skill)
    mock_brain.generate_structured.assert_called()
