"""Unit tests — CodeReviewerAgent routing (zero I/O, all Skills mocked)."""

from unittest.mock import AsyncMock

import pytest

from software_factory_poc.core.application.agents.code_reviewer.code_reviewer_agent import (
    CodeReviewerAgent,
)
from software_factory_poc.core.application.agents.common.agent_execution_mode import (
    AgentExecutionMode,
)
from software_factory_poc.core.application.skills.review.analyze_code_review_skill import (
    AnalyzeCodeReviewInput,
)
from software_factory_poc.core.application.skills.review.fetch_review_diff_skill import (
    FetchReviewDiffInput,
    FetchReviewDiffOutput,
)
from software_factory_poc.core.application.skills.review.publish_code_review_skill import (
    PublishCodeReviewInput,
)
from software_factory_poc.core.application.skills.review.validate_review_context_skill import (
    ReviewContext,
)
from software_factory_poc.core.domain.mission.entities.mission import Mission
from software_factory_poc.core.domain.mission.value_objects.task_description import TaskDescription
from software_factory_poc.core.domain.quality.code_review_report import CodeReviewReport

# ── Helpers ──


def _make_mission(key: str = "PROJ-200") -> Mission:
    return Mission(
        id="20001",
        key=key,
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
                },
            },
        ),
    )


def _make_review_context() -> ReviewContext:
    return ReviewContext(
        mr_url="https://gitlab.example.com/merge_requests/55",
        gitlab_project_id="42",
        mr_iid="55",
    )


def _make_report(approved: bool = True) -> CodeReviewReport:
    return CodeReviewReport(
        is_approved=approved,
        summary="Looks good" if approved else "Needs changes",
        comments=[],
    )


def _build_agent(
    execution_mode: AgentExecutionMode = AgentExecutionMode.DETERMINISTIC,
) -> tuple[CodeReviewerAgent, dict[str, AsyncMock]]:
    """Build a CodeReviewerAgent with all dependencies mocked."""
    mocks = {
        "vcs": AsyncMock(),
        "tracker": AsyncMock(),
        "research": AsyncMock(),
        "brain": AsyncMock(),
        "validate_context": AsyncMock(),
        "fetch_diff": AsyncMock(),
        "analyze": AsyncMock(),
        "publish": AsyncMock(),
        "loop_runner": AsyncMock(),
    }

    agent = CodeReviewerAgent(
        vcs=mocks["vcs"],
        tracker=mocks["tracker"],
        research=mocks["research"],
        brain=mocks["brain"],
        validate_context=mocks["validate_context"],
        fetch_diff=mocks["fetch_diff"],
        analyze=mocks["analyze"],
        publish=mocks["publish"],
        loop_runner=mocks["loop_runner"],
        priority_models=["openai:gpt-4o"],
        execution_mode=execution_mode,
    )
    return agent, mocks


# ══════════════════════════════════════════════════════════════════════
# Deterministic Routing
# ══════════════════════════════════════════════════════════════════════


class TestDeterministicRouting:
    """Verify the agent orchestrates the 4-skill pipeline in order."""

    async def test_full_pipeline_calls_all_skills(self) -> None:
        agent, mocks = _build_agent()
        mission = _make_mission()
        ctx = _make_review_context()
        report = _make_report()

        mocks["validate_context"].execute.return_value = ctx
        mocks["fetch_diff"].execute.return_value = FetchReviewDiffOutput(
            mr_diff="diff content", conventions="style guide"
        )
        mocks["analyze"].execute.return_value = report
        mocks["publish"].execute.return_value = None

        await agent.execute_flow(mission)

        mocks["validate_context"].execute.assert_awaited_once_with(mission)
        mocks["fetch_diff"].execute.assert_awaited_once()
        mocks["analyze"].execute.assert_awaited_once()
        mocks["publish"].execute.assert_awaited_once()

    async def test_fetch_diff_receives_correct_input(self) -> None:
        agent, mocks = _build_agent()
        mission = _make_mission()
        ctx = _make_review_context()
        report = _make_report()

        mocks["validate_context"].execute.return_value = ctx
        mocks["fetch_diff"].execute.return_value = FetchReviewDiffOutput(
            mr_diff="diff", conventions="conv"
        )
        mocks["analyze"].execute.return_value = report
        mocks["publish"].execute.return_value = None

        await agent.execute_flow(mission)

        call_args = mocks["fetch_diff"].execute.call_args[0][0]
        assert isinstance(call_args, FetchReviewDiffInput)
        assert call_args.mr_iid == "55"
        assert call_args.context_query == mission.summary

    async def test_analyze_receives_correct_input(self) -> None:
        agent, mocks = _build_agent()
        mission = _make_mission()
        ctx = _make_review_context()
        report = _make_report()

        mocks["validate_context"].execute.return_value = ctx
        mocks["fetch_diff"].execute.return_value = FetchReviewDiffOutput(
            mr_diff="the diff", conventions="the conventions"
        )
        mocks["analyze"].execute.return_value = report

        await agent.execute_flow(mission)

        call_args = mocks["analyze"].execute.call_args[0][0]
        assert isinstance(call_args, AnalyzeCodeReviewInput)
        assert call_args.mr_diff == "the diff"
        assert call_args.conventions == "the conventions"
        assert call_args.priority_models == ["openai:gpt-4o"]

    async def test_publish_receives_correct_input(self) -> None:
        agent, mocks = _build_agent()
        mission = _make_mission()
        ctx = _make_review_context()
        report = _make_report(approved=False)

        mocks["validate_context"].execute.return_value = ctx
        mocks["fetch_diff"].execute.return_value = FetchReviewDiffOutput(
            mr_diff="diff", conventions="conv"
        )
        mocks["analyze"].execute.return_value = report

        await agent.execute_flow(mission)

        call_args = mocks["publish"].execute.call_args[0][0]
        assert isinstance(call_args, PublishCodeReviewInput)
        assert call_args.mission_key == "PROJ-200"
        assert call_args.mr_iid == "55"
        assert call_args.report is report

    async def test_skill_failure_reports_to_tracker(self) -> None:
        agent, mocks = _build_agent()
        mission = _make_mission()

        mocks["validate_context"].execute.side_effect = ValueError("Missing metadata")

        with pytest.raises(ValueError, match="Missing metadata"):
            await agent.execute_flow(mission)

        mocks["tracker"].add_comment.assert_awaited_once()


# ══════════════════════════════════════════════════════════════════════
# Agentic Routing
# ══════════════════════════════════════════════════════════════════════


class TestAgenticRouting:
    """Verify the agent delegates to the loop runner in REACT_LOOP mode."""

    async def test_react_mode_delegates_to_loop_runner(self) -> None:
        agent, mocks = _build_agent(execution_mode=AgentExecutionMode.REACT_LOOP)
        mission = _make_mission()

        mocks["vcs"].get_mcp_tools.return_value = [
            {"type": "function", "function": {"name": "vcs_get_diff"}}
        ]
        mocks["tracker"].get_mcp_tools.return_value = []
        mocks["research"].get_mcp_tools.return_value = []
        mocks["loop_runner"].run_loop.return_value = "review done"

        await agent.execute_flow(mission)

        mocks["loop_runner"].run_loop.assert_awaited_once()
        call_kwargs = mocks["loop_runner"].run_loop.call_args[1]
        assert call_kwargs["mission"] is mission
        assert len(call_kwargs["available_tools"]) == 1

    async def test_react_mode_does_not_call_deterministic_skills(self) -> None:
        agent, mocks = _build_agent(execution_mode=AgentExecutionMode.REACT_LOOP)
        mission = _make_mission()

        mocks["vcs"].get_mcp_tools.return_value = []
        mocks["tracker"].get_mcp_tools.return_value = []
        mocks["research"].get_mcp_tools.return_value = []
        mocks["loop_runner"].run_loop.return_value = "done"

        await agent.execute_flow(mission)

        mocks["validate_context"].execute.assert_not_awaited()
        mocks["fetch_diff"].execute.assert_not_awaited()
        mocks["analyze"].execute.assert_not_awaited()
        mocks["publish"].execute.assert_not_awaited()
