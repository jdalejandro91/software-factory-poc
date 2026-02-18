"""Unit tests — CodeReviewDeterministicWorkflow (all tools mocked)."""

from unittest.mock import AsyncMock

import pytest

from software_factory_poc.core.application.exceptions import WorkflowExecutionError
from software_factory_poc.core.application.skills.review.analyze_code_review_skill import (
    AnalyzeCodeReviewInput,
)
from software_factory_poc.core.application.workflows.review.code_review_deterministic_workflow import (
    CodeReviewDeterministicWorkflow,
)
from software_factory_poc.core.domain.delivery import FileChangesDTO
from software_factory_poc.core.domain.mission import Mission, TaskDescription
from software_factory_poc.core.domain.quality import CodeReviewReport

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
def mock_analyze() -> AsyncMock:
    return AsyncMock()


@pytest.fixture()
def workflow(
    mock_vcs: AsyncMock,
    mock_tracker: AsyncMock,
    mock_docs: AsyncMock,
    mock_analyze: AsyncMock,
) -> CodeReviewDeterministicWorkflow:
    return CodeReviewDeterministicWorkflow(
        vcs=mock_vcs,
        tracker=mock_tracker,
        docs=mock_docs,
        analyze=mock_analyze,
        priority_models=["openai:gpt-4o"],
    )


@pytest.fixture()
def mission() -> Mission:
    return Mission(
        id="20001",
        key="PROJ-200",
        summary="Review MR for authentication module",
        status="In Progress",
        project_key="PROJ",
        issue_type="Code Review",
        description=TaskDescription(
            raw_content="Review the auth module MR",
            config={
                "code_review_params": {
                    "review_request_url": "https://gitlab.example.com/merge_requests/55",
                    "gitlab_project_id": "42",
                    "source_branch_name": "feature/proj-200-auth",
                },
            },
        ),
    )


@pytest.fixture()
def sample_file_changes() -> list[FileChangesDTO]:
    return [
        FileChangesDTO(
            old_path="src/auth.py",
            new_path="src/auth.py",
            hunks=["@@ -1 +1,3 @@\n import os\n+import json\n+import yaml"],
            added_lines=[2, 3],
            removed_lines=[],
        ),
    ]


@pytest.fixture()
def approved_report() -> CodeReviewReport:
    return CodeReviewReport(is_approved=True, summary="LGTM", comments=[])


@pytest.fixture()
def rejected_report() -> CodeReviewReport:
    return CodeReviewReport(is_approved=False, summary="Needs work", comments=[])


def _setup_happy_path(
    mock_vcs: AsyncMock,
    mock_docs: AsyncMock,
    mock_analyze: AsyncMock,
    report: CodeReviewReport,
    file_changes: list[FileChangesDTO],
) -> None:
    """Configure mocks for a successful full pipeline run."""
    mock_vcs.validate_branch_existence.return_value = True
    mock_vcs.validate_merge_request_existence.return_value = True
    mock_vcs.get_original_branch_code.return_value = []
    mock_vcs.get_updated_code_diff.return_value = file_changes
    mock_docs.get_architecture_context.return_value = "conventions"
    mock_analyze.execute.return_value = report


# ══════════════════════════════════════════════════════════════════════
# Full Pipeline
# ══════════════════════════════════════════════════════════════════════


class TestFullPipeline:
    """Verify the workflow orchestrates all steps correctly."""

    @pytest.mark.asyncio
    async def test_full_pipeline_calls_all_tools(
        self,
        workflow: CodeReviewDeterministicWorkflow,
        mock_vcs: AsyncMock,
        mock_tracker: AsyncMock,
        mock_docs: AsyncMock,
        mock_analyze: AsyncMock,
        mission: Mission,
        approved_report: CodeReviewReport,
        sample_file_changes: list[FileChangesDTO],
    ) -> None:
        _setup_happy_path(mock_vcs, mock_docs, mock_analyze, approved_report, sample_file_changes)

        await workflow.execute(mission)

        mock_tracker.add_comment.assert_awaited()
        mock_vcs.validate_branch_existence.assert_awaited_once_with("feature/proj-200-auth")
        mock_vcs.validate_merge_request_existence.assert_awaited_once_with("55")
        mock_vcs.get_original_branch_code.assert_awaited_once_with("42", "feature/proj-200-auth")
        mock_vcs.get_updated_code_diff.assert_awaited_once_with("55")
        mock_docs.get_architecture_context.assert_awaited_once()
        mock_analyze.execute.assert_awaited_once()
        mock_vcs.publish_review.assert_awaited_once_with("55", approved_report)
        mock_tracker.update_status.assert_awaited_once_with("PROJ-200", "Done")

    @pytest.mark.asyncio
    async def test_rejected_report_transitions_to_changes_requested(
        self,
        workflow: CodeReviewDeterministicWorkflow,
        mock_vcs: AsyncMock,
        mock_tracker: AsyncMock,
        mock_docs: AsyncMock,
        mock_analyze: AsyncMock,
        mission: Mission,
        rejected_report: CodeReviewReport,
        sample_file_changes: list[FileChangesDTO],
    ) -> None:
        _setup_happy_path(mock_vcs, mock_docs, mock_analyze, rejected_report, sample_file_changes)

        await workflow.execute(mission)

        mock_tracker.update_status.assert_awaited_once_with("PROJ-200", "Changes Requested")

    @pytest.mark.asyncio
    async def test_analyze_skill_receives_correct_input(
        self,
        workflow: CodeReviewDeterministicWorkflow,
        mock_vcs: AsyncMock,
        mock_docs: AsyncMock,
        mock_analyze: AsyncMock,
        mission: Mission,
        approved_report: CodeReviewReport,
        sample_file_changes: list[FileChangesDTO],
    ) -> None:
        _setup_happy_path(mock_vcs, mock_docs, mock_analyze, approved_report, sample_file_changes)
        mock_docs.get_architecture_context.return_value = "conventions text"

        await workflow.execute(mission)

        call_args = mock_analyze.execute.call_args[0][0]
        assert isinstance(call_args, AnalyzeCodeReviewInput)
        assert call_args.mission.summary == "Review MR for authentication module"
        assert call_args.mission.key == "PROJ-200"
        assert "src/auth.py" in call_args.mr_diff
        assert call_args.conventions == "conventions text"
        assert call_args.priority_models == ["openai:gpt-4o"]
        assert (
            call_args.code_review_params["mr_url"] == "https://gitlab.example.com/merge_requests/55"
        )
        assert call_args.code_review_params["project_id"] == "42"
        assert call_args.code_review_params["branch"] == "feature/proj-200-auth"

    @pytest.mark.asyncio
    async def test_error_wraps_in_workflow_execution_error(
        self,
        workflow: CodeReviewDeterministicWorkflow,
        mock_vcs: AsyncMock,
        mock_tracker: AsyncMock,
        mission: Mission,
    ) -> None:
        mock_vcs.validate_branch_existence.side_effect = RuntimeError("VCS down")

        with pytest.raises(WorkflowExecutionError):
            await workflow.execute(mission)

        error_calls = mock_tracker.add_comment.call_args_list
        assert any("VCS down" in str(c) for c in error_calls)

    @pytest.mark.asyncio
    async def test_success_comment_includes_verdict(
        self,
        workflow: CodeReviewDeterministicWorkflow,
        mock_vcs: AsyncMock,
        mock_tracker: AsyncMock,
        mock_docs: AsyncMock,
        mock_analyze: AsyncMock,
        mission: Mission,
        approved_report: CodeReviewReport,
        sample_file_changes: list[FileChangesDTO],
    ) -> None:
        _setup_happy_path(mock_vcs, mock_docs, mock_analyze, approved_report, sample_file_changes)

        await workflow.execute(mission)

        success_comment = mock_tracker.add_comment.call_args_list[-1][0][1]
        assert "APPROVED" in success_comment
        assert "LGTM" in success_comment


# ══════════════════════════════════════════════════════════════════════
# MR Guardrail Tests
# ══════════════════════════════════════════════════════════════════════


class TestMrGuardrail:
    """Verify the MR validation guardrail halts the workflow correctly."""

    @pytest.mark.asyncio
    async def test_halts_when_mr_not_found(
        self,
        workflow: CodeReviewDeterministicWorkflow,
        mock_vcs: AsyncMock,
        mock_tracker: AsyncMock,
        mock_docs: AsyncMock,
        mock_analyze: AsyncMock,
        mission: Mission,
    ) -> None:
        mock_vcs.validate_branch_existence.return_value = True
        mock_vcs.validate_merge_request_existence.return_value = False

        await workflow.execute(mission)  # Should NOT raise (halted gracefully)

        mock_tracker.add_comment.assert_awaited()
        halt_comment = mock_tracker.add_comment.call_args_list[-1][0][1]
        assert "no existe o esta cerrado" in halt_comment
        mock_vcs.get_updated_code_diff.assert_not_awaited()
        mock_analyze.execute.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_proceeds_when_mr_exists(
        self,
        workflow: CodeReviewDeterministicWorkflow,
        mock_vcs: AsyncMock,
        mock_docs: AsyncMock,
        mock_analyze: AsyncMock,
        mission: Mission,
        approved_report: CodeReviewReport,
        sample_file_changes: list[FileChangesDTO],
    ) -> None:
        _setup_happy_path(mock_vcs, mock_docs, mock_analyze, approved_report, sample_file_changes)

        await workflow.execute(mission)

        mock_vcs.get_updated_code_diff.assert_awaited_once()
        mock_analyze.execute.assert_awaited_once()


# ══════════════════════════════════════════════════════════════════════
# Step Method Unit Tests
# ══════════════════════════════════════════════════════════════════════


class TestStepMethods:
    """Verify individual step methods / helpers in isolation."""

    def test_validate_metadata_extracts_yaml(
        self, workflow: CodeReviewDeterministicWorkflow, mission: Mission
    ) -> None:
        parsed = workflow._step_1_validate_metadata(mission)

        assert parsed["mr_url"] == "https://gitlab.example.com/merge_requests/55"
        assert parsed["project_id"] == "42"
        assert parsed["branch"] == "feature/proj-200-auth"
        assert parsed["mr_iid"] == "55"

    def test_validate_metadata_raises_on_missing_params(
        self, workflow: CodeReviewDeterministicWorkflow
    ) -> None:
        bad_mission = Mission(
            id="1",
            key="X-1",
            summary="s",
            status="s",
            project_key="X",
            issue_type="CR",
            description=TaskDescription(raw_content="", config={}),
        )
        with pytest.raises(WorkflowExecutionError, match="Missing code_review_params"):
            workflow._step_1_validate_metadata(bad_mission)

    @pytest.mark.asyncio
    async def test_validate_branch_passes_when_exists(
        self,
        workflow: CodeReviewDeterministicWorkflow,
        mock_vcs: AsyncMock,
    ) -> None:
        mock_vcs.validate_branch_existence.return_value = True

        await workflow._validate_branch("feature/x", "https://gitlab.com/mr/1")
        mock_vcs.validate_branch_existence.assert_awaited_once_with("feature/x")

    @pytest.mark.asyncio
    async def test_validate_branch_raises_when_missing(
        self,
        workflow: CodeReviewDeterministicWorkflow,
        mock_vcs: AsyncMock,
    ) -> None:
        mock_vcs.validate_branch_existence.return_value = False

        with pytest.raises(WorkflowExecutionError, match="not found"):
            await workflow._validate_branch("feature/gone", "https://gitlab.com/mr/1")

    @pytest.mark.asyncio
    async def test_validate_branch_raises_on_empty(
        self, workflow: CodeReviewDeterministicWorkflow
    ) -> None:
        with pytest.raises(WorkflowExecutionError, match="empty"):
            await workflow._validate_branch("", "https://gitlab.com/mr/1")

    def test_extract_mr_iid_from_url(self) -> None:
        assert (
            CodeReviewDeterministicWorkflow._extract_mr_iid("https://gitlab.com/merge_requests/42")
            == "42"
        )

    def test_extract_mr_iid_from_plain_number(self) -> None:
        assert CodeReviewDeterministicWorkflow._extract_mr_iid("99") == "99"

    def test_extract_mr_iid_raises_on_invalid(self) -> None:
        with pytest.raises(WorkflowExecutionError, match="Cannot extract"):
            CodeReviewDeterministicWorkflow._extract_mr_iid("not-a-url")

    @pytest.mark.asyncio
    async def test_fetch_context_delegates_to_docs(
        self,
        workflow: CodeReviewDeterministicWorkflow,
        mock_docs: AsyncMock,
    ) -> None:
        mock_docs.get_architecture_context.return_value = "arch ctx"

        result = await workflow._step_5_fetch_context("my-service")

        assert result == "arch ctx"
        mock_docs.get_architecture_context.assert_awaited_once_with(page_id="my-service")

    def test_file_changes_to_diff_text(self) -> None:
        changes = [
            FileChangesDTO(
                old_path="a.py",
                new_path="a.py",
                hunks=["@@ -1 +1,2 @@\n line1\n+line2"],
                added_lines=[2],
                removed_lines=[],
            ),
        ]
        result = CodeReviewDeterministicWorkflow._file_changes_to_diff_text(changes)
        assert "--- a.py" in result
        assert "+++ a.py" in result
        assert "+line2" in result

    def test_file_changes_to_diff_text_new_file(self) -> None:
        changes = [
            FileChangesDTO(
                old_path=None,
                new_path="new.py",
                hunks=["@@ -0 +1 @@\n+content"],
                added_lines=[1],
                removed_lines=[],
            ),
        ]
        result = CodeReviewDeterministicWorkflow._file_changes_to_diff_text(changes)
        assert "--- /dev/null" in result
        assert "+++ new.py" in result
