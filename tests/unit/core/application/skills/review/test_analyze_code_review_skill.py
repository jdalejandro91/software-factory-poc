"""Unit tests — AnalyzeCodeReviewSkill (zero I/O, AsyncMock for Ports)."""

from unittest.mock import AsyncMock, MagicMock

from software_factory_poc.core.application.skills.review.analyze_code_review_skill import (
    AnalyzeCodeReviewInput,
    AnalyzeCodeReviewSkill,
)
from software_factory_poc.core.application.skills.review.contracts.code_reviewer_contracts import (
    CodeIssueSchema,
    CodeReviewResponseSchema,
)
from software_factory_poc.core.domain.mission import Mission, TaskDescription
from software_factory_poc.core.domain.quality import ReviewSeverity


def _make_mission() -> Mission:
    return Mission(
        id="10001",
        key="PROJ-100",
        summary="Review auth module",
        status="In Progress",
        project_key="PROJ",
        issue_type="Code Review",
        description=TaskDescription(
            raw_content="Detailed review description",
            config={
                "code_review_params": {
                    "review_request_url": "https://gitlab.example.com/merge_requests/10",
                    "gitlab_project_id": "42",
                    "source_branch_name": "feature/proj-100-auth",
                },
            },
        ),
    )


def _make_input() -> AnalyzeCodeReviewInput:
    return AnalyzeCodeReviewInput(
        mission=_make_mission(),
        mr_diff="diff content",
        conventions="coding standards",
        priority_models=["openai:gpt-4o"],
        code_review_params={"mr_url": "https://gitlab.example.com/merge_requests/10"},
    )


class TestAnalyzeCodeReviewSkill:
    async def test_returns_approved_report(self) -> None:
        brain = AsyncMock()
        prompt_builder = MagicMock()
        prompt_builder.build_system_prompt.return_value = "system prompt"
        prompt_builder.build_analysis_prompt.return_value = "user prompt"

        schema = CodeReviewResponseSchema(
            is_approved=True,
            summary="Code looks good",
            issues=[],
        )
        brain.generate_structured.return_value = schema

        skill = AnalyzeCodeReviewSkill(brain=brain, prompt_builder=prompt_builder)
        report = await skill.execute(_make_input())

        assert report.is_approved is True
        assert report.summary == "Code looks good"
        assert len(report.comments) == 0

    async def test_critical_issue_forces_rejection(self) -> None:
        brain = AsyncMock()
        prompt_builder = MagicMock()
        prompt_builder.build_system_prompt.return_value = "sys"
        prompt_builder.build_analysis_prompt.return_value = "usr"

        schema = CodeReviewResponseSchema(
            is_approved=True,
            summary="Looks fine",
            issues=[
                CodeIssueSchema(
                    file_path="src/auth.py",
                    description="SQL injection",
                    suggestion="Use parameterized queries",
                    severity="CRITICAL",
                    line_number=42,
                ),
            ],
        )
        brain.generate_structured.return_value = schema

        skill = AnalyzeCodeReviewSkill(brain=brain, prompt_builder=prompt_builder)
        report = await skill.execute(_make_input())

        assert report.is_approved is False
        assert len(report.comments) == 1
        assert report.comments[0].severity == ReviewSeverity.CRITICAL

    async def test_calls_brain_with_combined_prompt(self) -> None:
        brain = AsyncMock()
        prompt_builder = MagicMock()
        prompt_builder.build_system_prompt.return_value = "SYS"
        prompt_builder.build_analysis_prompt.return_value = "USR"
        brain.generate_structured.return_value = CodeReviewResponseSchema(
            is_approved=True, summary="ok", issues=[]
        )

        skill = AnalyzeCodeReviewSkill(brain=brain, prompt_builder=prompt_builder)
        await skill.execute(_make_input())

        brain.generate_structured.assert_awaited_once()
        call_kwargs = brain.generate_structured.call_args[1]
        assert "SYS" in call_kwargs["prompt"]
        assert "USR" in call_kwargs["prompt"]

    async def test_builder_receives_mission_object(self) -> None:
        brain = AsyncMock()
        prompt_builder = MagicMock()
        prompt_builder.build_system_prompt.return_value = "SYS"
        prompt_builder.build_analysis_prompt.return_value = "USR"
        brain.generate_structured.return_value = CodeReviewResponseSchema(
            is_approved=True, summary="ok", issues=[]
        )

        skill = AnalyzeCodeReviewSkill(brain=brain, prompt_builder=prompt_builder)
        inp = _make_input()
        await skill.execute(inp)

        call_kwargs = prompt_builder.build_analysis_prompt.call_args[1]
        assert isinstance(call_kwargs["mission"], Mission)
        assert call_kwargs["mission"].key == "PROJ-100"
