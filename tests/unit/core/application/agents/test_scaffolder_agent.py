"""Unit tests — ScaffolderAgent dual-flow (zero I/O, all Skills mocked)."""

from unittest.mock import AsyncMock

import pytest

from software_factory_poc.core.application.agents.common.agent_config import (
    ScaffolderAgentConfig,
)
from software_factory_poc.core.application.agents.common.agent_execution_mode import (
    AgentExecutionMode,
)
from software_factory_poc.core.application.agents.scaffolder.contracts.scaffolder_contracts import (
    FileSchemaDTO,
    ScaffoldingResponseSchema,
)
from software_factory_poc.core.application.agents.scaffolder.scaffolder_agent import ScaffolderAgent
from software_factory_poc.core.application.skills.scaffold.generate_scaffold_plan_skill import (
    GenerateScaffoldPlanInput,
)
from software_factory_poc.core.domain.delivery import CommitIntent
from software_factory_poc.core.domain.mission import Mission, TaskDescription
from software_factory_poc.core.domain.shared.skill_type import SkillType
from software_factory_poc.core.domain.shared.tool_type import ToolType

# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture()
def agent_config() -> ScaffolderAgentConfig:
    return ScaffolderAgentConfig(priority_models=["openai:gpt-4o"])


@pytest.fixture()
def mock_tools() -> dict[ToolType, AsyncMock]:
    return {
        ToolType.VCS: AsyncMock(),
        ToolType.TRACKER: AsyncMock(),
        ToolType.DOCS: AsyncMock(),
        ToolType.BRAIN: AsyncMock(),
    }


@pytest.fixture()
def mock_skills() -> dict[SkillType, AsyncMock]:
    return {SkillType.GENERATE_SCAFFOLD_PLAN: AsyncMock()}


@pytest.fixture()
def agent(
    agent_config: ScaffolderAgentConfig,
    mock_tools: dict[ToolType, AsyncMock],
    mock_skills: dict[SkillType, AsyncMock],
) -> ScaffolderAgent:
    return ScaffolderAgent(config=agent_config, tools=mock_tools, skills=mock_skills)


@pytest.fixture()
def mission() -> Mission:
    return Mission(
        id="10001",
        key="PROJ-100",
        summary="Create microservice scaffolding",
        status="To Do",
        project_key="PROJ",
        issue_type="Task",
        description=TaskDescription(
            raw_content="Create scaffolding for my-service",
            config={
                "parameters": {"service_name": "my-service"},
                "target": {
                    "gitlab_project_id": "42",
                    "default_branch": "main",
                },
            },
        ),
    )


@pytest.fixture()
def scaffold_plan() -> ScaffoldingResponseSchema:
    return ScaffoldingResponseSchema(
        branch_name="feature/proj-100-my-service",
        commit_message="feat: scaffold my-service",
        files=[
            FileSchemaDTO(path="src/main.py", content="print('hello')", is_new=True),
        ],
    )


# ══════════════════════════════════════════════════════════════════════
# Deterministic Pipeline
# ══════════════════════════════════════════════════════════════════════


class TestDeterministicPipeline:
    """Verify the agent orchestrates the full deterministic pipeline."""

    @pytest.mark.asyncio
    async def test_full_pipeline_calls_all_tools_in_order(
        self,
        agent: ScaffolderAgent,
        mock_tools: dict[ToolType, AsyncMock],
        mock_skills: dict[SkillType, AsyncMock],
        mission: Mission,
        scaffold_plan: ScaffoldingResponseSchema,
    ) -> None:
        mock_tools[ToolType.VCS].validate_branch_existence.return_value = False
        mock_tools[ToolType.DOCS].get_architecture_context.return_value = "arch context"
        mock_skills[SkillType.GENERATE_SCAFFOLD_PLAN].execute.return_value = scaffold_plan
        mock_tools[ToolType.VCS].create_branch.return_value = "https://gitlab.com/branch"
        mock_tools[ToolType.VCS].commit_changes.return_value = "abc123"
        mock_tools[ToolType.VCS].create_merge_request.return_value = "https://gitlab.com/mr/1"

        await agent.run(mission)

        mock_tools[ToolType.VCS].validate_branch_existence.assert_awaited_once()
        mock_tools[ToolType.DOCS].get_architecture_context.assert_awaited_once_with("my-service")
        mock_skills[SkillType.GENERATE_SCAFFOLD_PLAN].execute.assert_awaited_once()
        mock_tools[ToolType.VCS].create_branch.assert_awaited_once()
        mock_tools[ToolType.VCS].commit_changes.assert_awaited_once()
        mock_tools[ToolType.VCS].create_merge_request.assert_awaited_once()
        mock_tools[ToolType.TRACKER].update_task_description.assert_awaited_once()
        assert mock_tools[ToolType.TRACKER].add_comment.call_count >= 2
        mock_tools[ToolType.TRACKER].update_status.assert_awaited_once_with("PROJ-100", "In Review")

    @pytest.mark.asyncio
    async def test_idempotency_abort_skips_remaining_steps(
        self,
        agent: ScaffolderAgent,
        mock_tools: dict[ToolType, AsyncMock],
        mock_skills: dict[SkillType, AsyncMock],
        mission: Mission,
    ) -> None:
        mock_tools[ToolType.VCS].validate_branch_existence.return_value = True

        await agent.run(mission)

        mock_tools[ToolType.VCS].validate_branch_existence.assert_awaited_once()
        mock_tools[ToolType.DOCS].get_architecture_context.assert_not_awaited()
        mock_skills[SkillType.GENERATE_SCAFFOLD_PLAN].execute.assert_not_awaited()
        mock_tools[ToolType.VCS].create_branch.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_generate_plan_receives_correct_input(
        self,
        agent: ScaffolderAgent,
        mock_tools: dict[ToolType, AsyncMock],
        mock_skills: dict[SkillType, AsyncMock],
        mission: Mission,
        scaffold_plan: ScaffoldingResponseSchema,
    ) -> None:
        mock_tools[ToolType.VCS].validate_branch_existence.return_value = False
        mock_tools[ToolType.DOCS].get_architecture_context.return_value = "arch context"
        mock_skills[SkillType.GENERATE_SCAFFOLD_PLAN].execute.return_value = scaffold_plan
        mock_tools[ToolType.VCS].create_branch.return_value = "https://gitlab.com/branch"
        mock_tools[ToolType.VCS].commit_changes.return_value = "abc123"
        mock_tools[ToolType.VCS].create_merge_request.return_value = "https://gitlab.com/mr/1"

        await agent.run(mission)

        call_args = mock_skills[SkillType.GENERATE_SCAFFOLD_PLAN].execute.call_args[0][0]
        assert isinstance(call_args, GenerateScaffoldPlanInput)
        assert call_args.mission is mission
        assert call_args.arch_context == "arch context"
        assert call_args.priority_models == ["openai:gpt-4o"]

    @pytest.mark.asyncio
    async def test_vcs_operations_receive_correct_input(
        self,
        agent: ScaffolderAgent,
        mock_tools: dict[ToolType, AsyncMock],
        mock_skills: dict[SkillType, AsyncMock],
        mission: Mission,
        scaffold_plan: ScaffoldingResponseSchema,
    ) -> None:
        mock_tools[ToolType.VCS].validate_branch_existence.return_value = False
        mock_tools[ToolType.DOCS].get_architecture_context.return_value = "arch"
        mock_skills[SkillType.GENERATE_SCAFFOLD_PLAN].execute.return_value = scaffold_plan
        mock_tools[ToolType.VCS].create_branch.return_value = "https://gitlab.com/branch"
        mock_tools[ToolType.VCS].commit_changes.return_value = "abc123"
        mock_tools[ToolType.VCS].create_merge_request.return_value = "https://gitlab.com/mr/1"

        await agent.run(mission)

        mock_tools[ToolType.VCS].create_branch.assert_awaited_once_with(
            "feature/proj-100-my-service", ref="main"
        )
        commit_arg = mock_tools[ToolType.VCS].commit_changes.call_args[0][0]
        assert isinstance(commit_arg, CommitIntent)
        assert len(commit_arg.files) == 1
        mock_tools[ToolType.VCS].create_merge_request.assert_awaited_once_with(
            source_branch="feature/proj-100-my-service",
            target_branch="main",
            title="feat: Scaffolding PROJ-100",
            description="Auto-generated by BrahMAS.\n\nCreate microservice scaffolding",
        )

    @pytest.mark.asyncio
    async def test_tracker_receives_correct_report_data(
        self,
        agent: ScaffolderAgent,
        mock_tools: dict[ToolType, AsyncMock],
        mock_skills: dict[SkillType, AsyncMock],
        mission: Mission,
        scaffold_plan: ScaffoldingResponseSchema,
    ) -> None:
        mock_tools[ToolType.VCS].validate_branch_existence.return_value = False
        mock_tools[ToolType.DOCS].get_architecture_context.return_value = "arch"
        mock_skills[SkillType.GENERATE_SCAFFOLD_PLAN].execute.return_value = scaffold_plan
        mock_tools[ToolType.VCS].create_branch.return_value = "https://gitlab.com/branch"
        mock_tools[ToolType.VCS].commit_changes.return_value = "abc123"
        mock_tools[ToolType.VCS].create_merge_request.return_value = "https://gitlab.com/mr/1"

        await agent.run(mission)

        desc_arg = mock_tools[ToolType.TRACKER].update_task_description.call_args[0][1]
        assert "code_review_params:" in desc_arg
        assert 'gitlab_project_id: "42"' in desc_arg
        last_comment = mock_tools[ToolType.TRACKER].add_comment.call_args_list[-1][0][1]
        assert "abc123" in last_comment
        assert "https://gitlab.com/mr/1" in last_comment

    @pytest.mark.asyncio
    async def test_skill_failure_propagates(
        self,
        agent: ScaffolderAgent,
        mock_tools: dict[ToolType, AsyncMock],
        mission: Mission,
    ) -> None:
        mock_tools[ToolType.VCS].validate_branch_existence.return_value = False
        mock_tools[ToolType.DOCS].get_architecture_context.side_effect = RuntimeError(
            "Confluence down"
        )

        with pytest.raises(RuntimeError, match="Confluence down"):
            await agent.run(mission)


# ══════════════════════════════════════════════════════════════════════
# Step Method Unit Tests
# ══════════════════════════════════════════════════════════════════════


class TestStepMethods:
    """Verify individual step methods in isolation."""

    @pytest.mark.asyncio
    async def test_build_branch_name_with_service(self) -> None:
        assert ScaffolderAgent._build_branch_name("PROJ-100", "my-service") == (
            "feature/proj-100-my-service"
        )

    @pytest.mark.asyncio
    async def test_build_branch_name_without_service(self) -> None:
        assert ScaffolderAgent._build_branch_name("PROJ-100") == "feature/proj-100-scaffolder"

    @pytest.mark.asyncio
    async def test_step_1_parse_mission(self, agent: ScaffolderAgent, mission: Mission) -> None:
        parsed = await agent._step_1_parse_mission(mission)

        assert parsed["service_name"] == "my-service"
        assert parsed["project_id"] == "42"
        assert parsed["target_branch"] == "main"
        assert parsed["branch_name"] == "feature/proj-100-my-service"

    @pytest.mark.asyncio
    async def test_step_3_returns_true_when_branch_exists(
        self,
        agent: ScaffolderAgent,
        mock_tools: dict[ToolType, AsyncMock],
        mission: Mission,
    ) -> None:
        mock_tools[ToolType.VCS].validate_branch_existence.return_value = True

        result = await agent._step_3_check_idempotency(mission, "feature/proj-100-my-service")

        assert result is True
        mock_tools[ToolType.TRACKER].add_comment.assert_awaited()
        mock_tools[ToolType.TRACKER].update_status.assert_awaited_once_with("PROJ-100", "In Review")

    @pytest.mark.asyncio
    async def test_step_3_returns_false_when_branch_missing(
        self,
        agent: ScaffolderAgent,
        mock_tools: dict[ToolType, AsyncMock],
        mission: Mission,
    ) -> None:
        mock_tools[ToolType.VCS].validate_branch_existence.return_value = False

        result = await agent._step_3_check_idempotency(mission, "feature/proj-100-my-service")

        assert result is False

    @pytest.mark.asyncio
    async def test_step_4_delegates_to_docs(
        self,
        agent: ScaffolderAgent,
        mock_tools: dict[ToolType, AsyncMock],
    ) -> None:
        mock_tools[ToolType.DOCS].get_architecture_context.return_value = "arch ctx"

        result = await agent._step_4_fetch_context("my-service")

        assert result == "arch ctx"
        mock_tools[ToolType.DOCS].get_architecture_context.assert_awaited_once_with("my-service")

    @pytest.mark.asyncio
    async def test_step_7_raises_on_empty_plan(self, agent: ScaffolderAgent) -> None:
        empty_plan = ScaffoldingResponseSchema(branch_name="b", commit_message="m", files=[])
        with pytest.raises(ValueError, match="0 files"):
            agent._step_7_validate_plan(empty_plan)


# ══════════════════════════════════════════════════════════════════════
# Agentic Routing
# ══════════════════════════════════════════════════════════════════════


class TestAgenticRouting:
    """Verify the agent correctly delegates to the loop runner in REACT_LOOP mode."""

    @pytest.mark.asyncio
    async def test_react_mode_delegates_to_loop_runner(
        self, mock_tools: dict[ToolType, AsyncMock], mock_skills: dict[SkillType, AsyncMock]
    ) -> None:
        config = ScaffolderAgentConfig(
            priority_models=["openai:gpt-4o"],
            execution_mode=AgentExecutionMode.REACT_LOOP,
        )
        agent = ScaffolderAgent(config=config, tools=mock_tools, skills=mock_skills)
        mission = Mission(
            id="10001",
            key="PROJ-100",
            summary="Create microservice scaffolding",
            status="To Do",
            project_key="PROJ",
            issue_type="Task",
            description=TaskDescription(
                raw_content="Create scaffolding for my-service",
                config={
                    "parameters": {"service_name": "my-service"},
                    "target": {"gitlab_project_id": "42", "default_branch": "main"},
                },
            ),
        )

        mock_loop_runner = AsyncMock()
        mock_loop_runner.run_loop.return_value = "done"
        agent._loop_runner = mock_loop_runner

        await agent.run(mission)

        mock_loop_runner.run_loop.assert_awaited_once()
        call_kwargs = mock_loop_runner.run_loop.call_args[1]
        assert call_kwargs["mission"] is mission
        assert call_kwargs["tools_registry"] is agent._tools
        assert call_kwargs["priority_models"] == ["openai:gpt-4o"]

    @pytest.mark.asyncio
    async def test_react_mode_does_not_call_deterministic_steps(
        self, mock_tools: dict[ToolType, AsyncMock], mock_skills: dict[SkillType, AsyncMock]
    ) -> None:
        config = ScaffolderAgentConfig(
            priority_models=["openai:gpt-4o"],
            execution_mode=AgentExecutionMode.REACT_LOOP,
        )
        agent = ScaffolderAgent(config=config, tools=mock_tools, skills=mock_skills)
        mission = Mission(
            id="10001",
            key="PROJ-100",
            summary="s",
            status="s",
            project_key="PROJ",
            issue_type="Task",
            description=TaskDescription(raw_content="x", config={"parameters": {}, "target": {}}),
        )

        mock_loop_runner = AsyncMock()
        mock_loop_runner.run_loop.return_value = "done"
        agent._loop_runner = mock_loop_runner

        await agent.run(mission)

        mock_skills[SkillType.GENERATE_SCAFFOLD_PLAN].execute.assert_not_awaited()
        mock_tools[ToolType.VCS].create_branch.assert_not_awaited()
        mock_tools[ToolType.TRACKER].update_status.assert_not_awaited()
