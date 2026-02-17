from unittest.mock import AsyncMock, MagicMock

import pytest

from software_factory_poc.core.application.agents.loops.agentic_loop_runner import (
    AgenticLoopRunner,
)
from software_factory_poc.core.application.agents.scaffolder.contracts.scaffolder_contracts import (
    FileSchemaDTO,
    ScaffoldingResponseSchema,
)
from software_factory_poc.core.application.agents.scaffolder.scaffolder_agent import ScaffolderAgent
from software_factory_poc.core.application.policies.tool_safety_policy import ToolSafetyPolicy
from software_factory_poc.core.application.skills.scaffold.apply_scaffold_delivery_skill import (
    ApplyScaffoldDeliverySkill,
)
from software_factory_poc.core.application.skills.scaffold.fetch_scaffold_context_skill import (
    FetchScaffoldContextSkill,
)
from software_factory_poc.core.application.skills.scaffold.generate_scaffold_plan_skill import (
    GenerateScaffoldPlanSkill,
)
from software_factory_poc.core.application.skills.scaffold.idempotency_check_skill import (
    IdempotencyCheckSkill,
)
from software_factory_poc.core.application.skills.scaffold.report_success_skill import (
    ReportSuccessSkill,
)
from software_factory_poc.core.domain.mission.entities.mission import Mission
from software_factory_poc.core.domain.mission.value_objects.task_description import TaskDescription


@pytest.mark.asyncio
async def test_scaffolder_agent_flow():
    """
    Integration test for ScaffolderAgent.execute_flow.
    Verifies the orchestration of Skills from Idempotency -> Context -> Plan -> Delivery -> Report.
    """

    # 1. Setup Mocks for Ports
    mock_vcs = AsyncMock()
    mock_vcs.validate_branch_existence.return_value = False
    mock_vcs.commit_changes.return_value = "commit-hash-123"
    mock_vcs.create_merge_request.return_value = "https://gitlab.com/mr/1"

    mock_tracker = AsyncMock()

    mock_research = AsyncMock()
    mock_research.get_architecture_context.return_value = "Architecture Guidelines..."

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

    # 3. Instantiate Agent with Skills
    agent = ScaffolderAgent(
        vcs=mock_vcs,
        tracker=mock_tracker,
        research=mock_research,
        brain=mock_brain,
        idempotency_check=IdempotencyCheckSkill(vcs=mock_vcs, tracker=mock_tracker),
        fetch_context=FetchScaffoldContextSkill(docs=mock_research),
        generate_plan=GenerateScaffoldPlanSkill(
            brain=mock_brain, prompt_builder=mock_prompt_builder
        ),
        apply_delivery=ApplyScaffoldDeliverySkill(vcs=mock_vcs),
        report_success=ReportSuccessSkill(tracker=mock_tracker),
        loop_runner=AgenticLoopRunner(brain=mock_brain, policy=ToolSafetyPolicy()),
        priority_models=["openai:gpt-4o"],
    )

    # 4. Execute Flow
    await agent.execute_flow(mission)

    # 5. Assertions

    # Tracker: Initial comment + Metadata + Success Msg + Status Update
    assert mock_tracker.add_comment.call_count >= 3
    mock_tracker.update_status.assert_called_with("POC-50", "In Review")

    # VCS: Branch validation -> Creation -> Commit -> MR
    mock_vcs.validate_branch_existence.assert_called()
    mock_vcs.create_branch.assert_called_with("feature/poc-50-user-service", ref="main")
    mock_vcs.commit_changes.assert_called()
    mock_vcs.create_merge_request.assert_called()

    # Brain: Research -> Prompt -> Generate
    mock_research.get_architecture_context.assert_called()
    mock_brain.generate_structured.assert_called()
