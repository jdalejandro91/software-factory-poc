"""Unit tests — ScaffoldingDeterministicWorkflow (all tools mocked)."""

from unittest.mock import AsyncMock

import pytest

from software_factory_poc.core.application.exceptions import (
    WorkflowExecutionError,
    WorkflowHaltedException,
)
from software_factory_poc.core.application.skills.scaffold.contracts.scaffolder_contracts import (
    FileSchemaDTO,
    ScaffoldingResponseSchema,
)
from software_factory_poc.core.application.skills.scaffold.generate_scaffold_plan_skill import (
    GenerateScaffoldPlanInput,
)
from software_factory_poc.core.application.workflows.scaffold.scaffolding_deterministic_workflow import (
    ScaffoldingDeterministicWorkflow,
)
from software_factory_poc.core.domain.delivery import CommitIntent
from software_factory_poc.core.domain.mission import Mission, TaskDescription

# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture()
def mock_vcs() -> AsyncMock:
    return AsyncMock()


@pytest.fixture()
def mock_tracker() -> AsyncMock:
    return AsyncMock()


@pytest.fixture()
def mock_docs() -> AsyncMock:
    return AsyncMock()


@pytest.fixture()
def mock_generate_plan() -> AsyncMock:
    return AsyncMock()


@pytest.fixture()
def workflow(
    mock_vcs: AsyncMock,
    mock_tracker: AsyncMock,
    mock_docs: AsyncMock,
    mock_generate_plan: AsyncMock,
) -> ScaffoldingDeterministicWorkflow:
    return ScaffoldingDeterministicWorkflow(
        vcs=mock_vcs,
        tracker=mock_tracker,
        docs=mock_docs,
        generate_plan=mock_generate_plan,
        priority_models=["openai:gpt-4o"],
    )


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
# Full Pipeline
# ══════════════════════════════════════════════════════════════════════


class TestFullPipeline:
    """Verify the workflow orchestrates all steps correctly."""

    @pytest.mark.asyncio
    async def test_full_pipeline_calls_all_tools(
        self,
        workflow: ScaffoldingDeterministicWorkflow,
        mock_vcs: AsyncMock,
        mock_tracker: AsyncMock,
        mock_docs: AsyncMock,
        mock_generate_plan: AsyncMock,
        mission: Mission,
        scaffold_plan: ScaffoldingResponseSchema,
    ) -> None:
        mock_vcs.validate_branch_existence.return_value = False
        mock_docs.get_architecture_context.return_value = "arch context"
        mock_generate_plan.execute.return_value = scaffold_plan
        mock_vcs.commit_changes.return_value = "abc123"
        mock_vcs.create_merge_request.return_value = "https://gitlab.com/mr/1"

        await workflow.execute(mission)

        mock_vcs.validate_branch_existence.assert_awaited_once()
        mock_docs.get_architecture_context.assert_awaited_once_with("my-service")
        mock_generate_plan.execute.assert_awaited_once()
        mock_vcs.create_branch.assert_awaited_once()
        mock_vcs.commit_changes.assert_awaited_once()
        mock_vcs.create_merge_request.assert_awaited_once()
        mock_tracker.update_task_description.assert_awaited_once()
        assert mock_tracker.add_comment.call_count >= 2
        mock_tracker.update_status.assert_awaited_once_with("PROJ-100", "In Review")

    @pytest.mark.asyncio
    async def test_idempotency_halts_gracefully(
        self,
        workflow: ScaffoldingDeterministicWorkflow,
        mock_vcs: AsyncMock,
        mock_docs: AsyncMock,
        mock_generate_plan: AsyncMock,
        mission: Mission,
    ) -> None:
        mock_vcs.validate_branch_existence.return_value = True

        await workflow.execute(mission)  # Should NOT raise

        mock_docs.get_architecture_context.assert_not_awaited()
        mock_generate_plan.execute.assert_not_awaited()
        mock_vcs.create_branch.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_generate_plan_receives_correct_input(
        self,
        workflow: ScaffoldingDeterministicWorkflow,
        mock_vcs: AsyncMock,
        mock_docs: AsyncMock,
        mock_generate_plan: AsyncMock,
        mission: Mission,
        scaffold_plan: ScaffoldingResponseSchema,
    ) -> None:
        mock_vcs.validate_branch_existence.return_value = False
        mock_docs.get_architecture_context.return_value = "arch context"
        mock_generate_plan.execute.return_value = scaffold_plan
        mock_vcs.commit_changes.return_value = "abc123"
        mock_vcs.create_merge_request.return_value = "https://gitlab.com/mr/1"

        await workflow.execute(mission)

        call_args = mock_generate_plan.execute.call_args[0][0]
        assert isinstance(call_args, GenerateScaffoldPlanInput)
        assert call_args.mission is mission
        assert call_args.arch_context == "arch context"
        assert call_args.priority_models == ["openai:gpt-4o"]

    @pytest.mark.asyncio
    async def test_vcs_operations_receive_correct_input(
        self,
        workflow: ScaffoldingDeterministicWorkflow,
        mock_vcs: AsyncMock,
        mock_docs: AsyncMock,
        mock_generate_plan: AsyncMock,
        mission: Mission,
        scaffold_plan: ScaffoldingResponseSchema,
    ) -> None:
        mock_vcs.validate_branch_existence.return_value = False
        mock_docs.get_architecture_context.return_value = "arch"
        mock_generate_plan.execute.return_value = scaffold_plan
        mock_vcs.commit_changes.return_value = "abc123"
        mock_vcs.create_merge_request.return_value = "https://gitlab.com/mr/1"

        await workflow.execute(mission)

        mock_vcs.create_branch.assert_awaited_once_with("feature/proj-100-my-service", ref="main")
        commit_arg = mock_vcs.commit_changes.call_args[0][0]
        assert isinstance(commit_arg, CommitIntent)
        assert len(commit_arg.files) == 1
        mock_vcs.create_merge_request.assert_awaited_once_with(
            source_branch="feature/proj-100-my-service",
            target_branch="main",
            title="feat: Scaffolding PROJ-100",
            description="Auto-generated by BrahMAS.\n\nCreate microservice scaffolding",
        )

    @pytest.mark.asyncio
    async def test_tracker_receives_correct_report(
        self,
        workflow: ScaffoldingDeterministicWorkflow,
        mock_vcs: AsyncMock,
        mock_tracker: AsyncMock,
        mock_docs: AsyncMock,
        mock_generate_plan: AsyncMock,
        mission: Mission,
        scaffold_plan: ScaffoldingResponseSchema,
    ) -> None:
        mock_vcs.validate_branch_existence.return_value = False
        mock_docs.get_architecture_context.return_value = "arch"
        mock_generate_plan.execute.return_value = scaffold_plan
        mock_vcs.commit_changes.return_value = "abc123"
        mock_vcs.create_merge_request.return_value = "https://gitlab.com/mr/1"

        await workflow.execute(mission)

        desc_arg = mock_tracker.update_task_description.call_args[0][1]
        assert "code_review_params:" in desc_arg
        assert 'gitlab_project_id: "42"' in desc_arg
        last_comment = mock_tracker.add_comment.call_args_list[-1][0][1]
        assert "abc123" in last_comment
        assert "https://gitlab.com/mr/1" in last_comment

    @pytest.mark.asyncio
    async def test_error_wraps_in_workflow_execution_error(
        self,
        workflow: ScaffoldingDeterministicWorkflow,
        mock_vcs: AsyncMock,
        mock_tracker: AsyncMock,
        mock_docs: AsyncMock,
        mission: Mission,
    ) -> None:
        mock_vcs.validate_branch_existence.return_value = False
        mock_docs.get_architecture_context.side_effect = RuntimeError("Confluence down")

        with pytest.raises(WorkflowExecutionError):
            await workflow.execute(mission)

        mock_tracker.add_comment.assert_awaited()


# ══════════════════════════════════════════════════════════════════════
# Step Method Unit Tests
# ══════════════════════════════════════════════════════════════════════


class TestStepMethods:
    """Verify individual step methods / helpers in isolation."""

    def test_build_branch_name_with_service(self) -> None:
        assert (
            ScaffoldingDeterministicWorkflow._build_branch_name("PROJ-100", "my-service")
            == "feature/proj-100-my-service"
        )

    def test_build_branch_name_without_service(self) -> None:
        assert (
            ScaffoldingDeterministicWorkflow._build_branch_name("PROJ-100")
            == "feature/proj-100-scaffolder"
        )

    def test_parse_mission(
        self,
        workflow: ScaffoldingDeterministicWorkflow,
        mission: Mission,
    ) -> None:
        parsed = workflow._parse_mission(mission)

        assert parsed["service_name"] == "my-service"
        assert parsed["project_id"] == "42"
        assert parsed["target_branch"] == "main"
        assert parsed["branch_name"] == "feature/proj-100-my-service"

    @pytest.mark.asyncio
    async def test_check_idempotency_halts_when_branch_exists(
        self,
        workflow: ScaffoldingDeterministicWorkflow,
        mock_vcs: AsyncMock,
        mock_tracker: AsyncMock,
        mission: Mission,
    ) -> None:
        mock_vcs.validate_branch_existence.return_value = True

        with pytest.raises(WorkflowHaltedException):
            await workflow._step_2_check_idempotency(mission, "feature/proj-100-my-service")

        mock_tracker.update_status.assert_awaited_once_with("PROJ-100", "In Review")

    @pytest.mark.asyncio
    async def test_check_idempotency_passes_when_no_branch(
        self,
        workflow: ScaffoldingDeterministicWorkflow,
        mock_vcs: AsyncMock,
        mission: Mission,
    ) -> None:
        mock_vcs.validate_branch_existence.return_value = False

        await workflow._step_2_check_idempotency(mission, "feature/proj-100-my-service")

    @pytest.mark.asyncio
    async def test_generate_plan_raises_on_empty_files(
        self,
        workflow: ScaffoldingDeterministicWorkflow,
        mock_generate_plan: AsyncMock,
        mission: Mission,
    ) -> None:
        mock_generate_plan.execute.return_value = ScaffoldingResponseSchema(
            branch_name="b", commit_message="m", files=[]
        )

        with pytest.raises(WorkflowExecutionError, match="0 files"):
            await workflow._step_4_generate_plan(mission, "ctx")

    @pytest.mark.asyncio
    async def test_fetch_context_delegates_to_docs(
        self,
        workflow: ScaffoldingDeterministicWorkflow,
        mock_docs: AsyncMock,
    ) -> None:
        mock_docs.get_architecture_context.return_value = "arch ctx"

        result = await workflow._step_3_fetch_context("my-service")

        assert result == "arch ctx"
        mock_docs.get_architecture_context.assert_awaited_once_with("my-service")
