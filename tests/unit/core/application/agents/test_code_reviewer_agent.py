"""Unit tests — CodeReviewerAgent dual-flow (zero I/O, all Skills mocked)."""

from unittest.mock import AsyncMock

import pytest

from software_factory_poc.core.application.agents.code_reviewer.code_reviewer_agent import (
    CodeReviewerAgent,
)
from software_factory_poc.core.application.agents.common.agent_config import (
    CodeReviewerAgentConfig,
)
from software_factory_poc.core.application.agents.common.agent_execution_mode import (
    AgentExecutionMode,
)
from software_factory_poc.core.domain.mission import Mission, TaskDescription
from software_factory_poc.core.domain.quality import CodeReviewReport
from software_factory_poc.core.domain.shared.skill_type import SkillType
from software_factory_poc.core.domain.shared.tool_type import ToolType

# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture()
def agent_config() -> CodeReviewerAgentConfig:
    return CodeReviewerAgentConfig(priority_models=["openai:gpt-4o"])


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
    return {SkillType.ANALYZE_CODE_REVIEW: AsyncMock()}


@pytest.fixture()
def agent(
    agent_config: CodeReviewerAgentConfig,
    mock_tools: dict[ToolType, AsyncMock],
    mock_skills: dict[SkillType, AsyncMock],
) -> CodeReviewerAgent:
    return CodeReviewerAgent(config=agent_config, tools=mock_tools, skills=mock_skills)


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
def approved_report() -> CodeReviewReport:
    return CodeReviewReport(is_approved=True, summary="LGTM", comments=[])


# ══════════════════════════════════════════════════════════════════════
# Step Methods (Deterministic Pipeline building blocks)
# ══════════════════════════════════════════════════════════════════════


class TestStepMethods:
    """Verify the individual step methods that compose the deterministic pipeline."""

    @pytest.mark.asyncio
    async def test_step_1_parse_mission_extracts_yaml(
        self, agent: CodeReviewerAgent, mission: Mission
    ) -> None:
        parsed = await agent._step_1_parse_mission(mission)

        assert parsed["mr_url"] == "https://gitlab.example.com/merge_requests/55"
        assert parsed["project_id"] == "42"
        assert parsed["branch"] == "feature/proj-200-auth"
        assert parsed["mr_iid"] == "55"

    @pytest.mark.asyncio
    async def test_step_1_raises_on_missing_params(self, agent: CodeReviewerAgent) -> None:
        bad_mission = Mission(
            id="1",
            key="X-1",
            summary="s",
            status="s",
            project_key="X",
            issue_type="CR",
            description=TaskDescription(raw_content="", config={}),
        )
        with pytest.raises(ValueError, match="Missing code_review_params"):
            await agent._step_1_parse_mission(bad_mission)

    @pytest.mark.asyncio
    async def test_step_2_report_start_comments_to_tracker(
        self,
        agent: CodeReviewerAgent,
        mock_tools: dict[ToolType, AsyncMock],
        mission: Mission,
    ) -> None:
        await agent._step_2_report_start(mission)

        mock_tools[ToolType.TRACKER].add_comment.assert_awaited_once()
        assert "PROJ-200" in mock_tools[ToolType.TRACKER].add_comment.call_args[0][0]

    @pytest.mark.asyncio
    async def test_step_3_validate_existence_passes_when_branch_exists(
        self,
        agent: CodeReviewerAgent,
        mock_tools: dict[ToolType, AsyncMock],
    ) -> None:
        mock_tools[ToolType.VCS].validate_branch_existence.return_value = True

        await agent._step_3_validate_existence("feature/x", "https://gitlab.com/mr/1")
        mock_tools[ToolType.VCS].validate_branch_existence.assert_awaited_once_with("feature/x")

    @pytest.mark.asyncio
    async def test_step_3_validate_existence_raises_when_missing(
        self,
        agent: CodeReviewerAgent,
        mock_tools: dict[ToolType, AsyncMock],
    ) -> None:
        mock_tools[ToolType.VCS].validate_branch_existence.return_value = False

        with pytest.raises(ValueError, match="not found"):
            await agent._step_3_validate_existence("feature/gone", "https://gitlab.com/mr/1")

    @pytest.mark.asyncio
    async def test_step_3_validate_existence_raises_on_empty_branch(
        self, agent: CodeReviewerAgent
    ) -> None:
        with pytest.raises(ValueError, match="empty"):
            await agent._step_3_validate_existence("", "https://gitlab.com/mr/1")

    @pytest.mark.asyncio
    async def test_extract_mr_iid_from_url(self) -> None:
        assert CodeReviewerAgent._extract_mr_iid("https://gitlab.com/merge_requests/42") == "42"

    @pytest.mark.asyncio
    async def test_extract_mr_iid_from_plain_number(self) -> None:
        assert CodeReviewerAgent._extract_mr_iid("99") == "99"

    @pytest.mark.asyncio
    async def test_extract_mr_iid_raises_on_invalid(self) -> None:
        with pytest.raises(ValueError, match="Cannot extract"):
            CodeReviewerAgent._extract_mr_iid("not-a-url")


# ══════════════════════════════════════════════════════════════════════
# Deterministic Pipeline (end-to-end)
# ══════════════════════════════════════════════════════════════════════


class TestDeterministicPipeline:
    """Verify the agent orchestrates all steps in order."""

    @pytest.mark.asyncio
    async def test_full_pipeline_calls_all_tools_in_order(
        self,
        agent: CodeReviewerAgent,
        mock_tools: dict[ToolType, AsyncMock],
        mock_skills: dict[SkillType, AsyncMock],
        mission: Mission,
        approved_report: CodeReviewReport,
    ) -> None:
        mock_tools[ToolType.VCS].validate_branch_existence.return_value = True
        mock_tools[ToolType.VCS].get_original_branch_code.return_value = []
        mock_tools[ToolType.VCS].get_updated_code_diff.return_value = "diff --git ..."
        mock_tools[ToolType.DOCS].get_architecture_context.return_value = "conventions"
        mock_skills[SkillType.ANALYZE_CODE_REVIEW].execute.return_value = approved_report

        await agent.run(mission)

        mock_tools[ToolType.TRACKER].add_comment.assert_awaited()
        mock_tools[ToolType.VCS].validate_branch_existence.assert_awaited_once_with(
            "feature/proj-200-auth"
        )
        mock_tools[ToolType.VCS].get_original_branch_code.assert_awaited_once_with(
            "42", "feature/proj-200-auth"
        )
        mock_tools[ToolType.VCS].get_updated_code_diff.assert_awaited_once_with("55")
        mock_tools[ToolType.DOCS].get_architecture_context.assert_awaited_once()
        mock_skills[SkillType.ANALYZE_CODE_REVIEW].execute.assert_awaited_once()
        mock_tools[ToolType.VCS].publish_review.assert_awaited_once_with("55", approved_report)
        mock_tools[ToolType.TRACKER].update_status.assert_awaited_once_with("PROJ-200", "Done")

    @pytest.mark.asyncio
    async def test_branch_validation_failure_propagates(
        self,
        agent: CodeReviewerAgent,
        mock_tools: dict[ToolType, AsyncMock],
        mission: Mission,
    ) -> None:
        mock_tools[ToolType.VCS].validate_branch_existence.return_value = False

        with pytest.raises(ValueError, match="not found"):
            await agent.run(mission)

    @pytest.mark.asyncio
    async def test_error_handler_posts_comment_to_tracker(
        self,
        agent: CodeReviewerAgent,
        mock_tools: dict[ToolType, AsyncMock],
        mission: Mission,
    ) -> None:
        mock_tools[ToolType.VCS].validate_branch_existence.side_effect = RuntimeError("VCS down")

        with pytest.raises(RuntimeError, match="VCS down"):
            await agent.run(mission)

        error_comment_calls = mock_tools[ToolType.TRACKER].add_comment.call_args_list
        assert any("VCS down" in str(c) for c in error_comment_calls)


# ══════════════════════════════════════════════════════════════════════
# Agentic Routing
# ══════════════════════════════════════════════════════════════════════


class TestAgenticRouting:
    """Verify the agent delegates to the loop runner in REACT_LOOP mode."""

    @pytest.mark.asyncio
    async def test_react_mode_delegates_to_loop_runner(
        self, mock_tools: dict[ToolType, AsyncMock], mock_skills: dict[SkillType, AsyncMock]
    ) -> None:
        config = CodeReviewerAgentConfig(
            priority_models=["openai:gpt-4o"],
            execution_mode=AgentExecutionMode.REACT_LOOP,
        )
        agent = CodeReviewerAgent(config=config, tools=mock_tools, skills=mock_skills)
        mission = Mission(
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

        mock_loop_runner = AsyncMock()
        mock_loop_runner.run_loop.return_value = "review done"
        agent._loop_runner = mock_loop_runner

        await agent.run(mission)

        mock_loop_runner.run_loop.assert_awaited_once()
        call_kwargs = mock_loop_runner.run_loop.call_args[1]
        assert call_kwargs["mission"] is mission
        assert call_kwargs["tools_registry"] is agent._tools

    @pytest.mark.asyncio
    async def test_react_mode_does_not_call_deterministic_skills(
        self, mock_tools: dict[ToolType, AsyncMock], mock_skills: dict[SkillType, AsyncMock]
    ) -> None:
        config = CodeReviewerAgentConfig(
            priority_models=["openai:gpt-4o"],
            execution_mode=AgentExecutionMode.REACT_LOOP,
        )
        agent = CodeReviewerAgent(config=config, tools=mock_tools, skills=mock_skills)
        mission = Mission(
            id="20001",
            key="PROJ-200",
            summary="s",
            status="s",
            project_key="PROJ",
            issue_type="CR",
            description=TaskDescription(
                raw_content="x",
                config={
                    "code_review_params": {
                        "review_request_url": "https://gitlab.com/merge_requests/1",
                        "gitlab_project_id": "1",
                        "source_branch_name": "b",
                    },
                },
            ),
        )

        mock_loop_runner = AsyncMock()
        mock_loop_runner.run_loop.return_value = "done"
        agent._loop_runner = mock_loop_runner

        await agent.run(mission)

        mock_skills[SkillType.ANALYZE_CODE_REVIEW].execute.assert_not_awaited()
        mock_tools[ToolType.VCS].publish_review.assert_not_awaited()
        mock_tools[ToolType.TRACKER].update_status.assert_not_awaited()
