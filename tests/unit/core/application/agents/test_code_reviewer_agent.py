"""Unit tests — CodeReviewerAgent dual-flow delegation (zero I/O, workflow mocked)."""

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
from software_factory_poc.core.domain.shared.skill_type import SkillType
from software_factory_poc.core.domain.shared.tool_type import ToolType

# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture()
def agent_config() -> CodeReviewerAgentConfig:
    return CodeReviewerAgentConfig(priority_models=["openai:gpt-4o"])


@pytest.fixture()
def mock_brain() -> AsyncMock:
    return AsyncMock()


@pytest.fixture()
def mock_tools() -> dict[ToolType, AsyncMock]:
    return {
        ToolType.VCS: AsyncMock(),
        ToolType.TRACKER: AsyncMock(),
        ToolType.DOCS: AsyncMock(),
    }


@pytest.fixture()
def mock_skills() -> dict[SkillType, AsyncMock]:
    return {SkillType.ANALYZE_CODE_REVIEW: AsyncMock()}


@pytest.fixture()
def mock_workflow() -> AsyncMock:
    return AsyncMock()


@pytest.fixture()
def agent(
    agent_config: CodeReviewerAgentConfig,
    mock_brain: AsyncMock,
    mock_tools: dict[ToolType, AsyncMock],
    mock_skills: dict[SkillType, AsyncMock],
    mock_workflow: AsyncMock,
) -> CodeReviewerAgent:
    return CodeReviewerAgent(
        config=agent_config,
        brain=mock_brain,
        tools=mock_tools,
        skills=mock_skills,
        deterministic_workflow=mock_workflow,
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


# ══════════════════════════════════════════════════════════════════════
# Deterministic Delegation
# ══════════════════════════════════════════════════════════════════════


class TestDeterministicDelegation:
    """Verify the agent delegates deterministic mode to the workflow."""

    @pytest.mark.asyncio
    async def test_deterministic_mode_delegates_to_workflow(
        self,
        agent: CodeReviewerAgent,
        mock_workflow: AsyncMock,
        mission: Mission,
    ) -> None:
        await agent.run(mission)

        mock_workflow.execute.assert_awaited_once_with(mission)

    @pytest.mark.asyncio
    async def test_workflow_error_propagates(
        self,
        agent: CodeReviewerAgent,
        mock_workflow: AsyncMock,
        mission: Mission,
    ) -> None:
        mock_workflow.execute.side_effect = RuntimeError("workflow failed")

        with pytest.raises(RuntimeError, match="workflow failed"):
            await agent.run(mission)


# ══════════════════════════════════════════════════════════════════════
# Agentic Routing
# ══════════════════════════════════════════════════════════════════════


class TestAgenticRouting:
    """Verify the agent delegates to the loop runner in REACT_LOOP mode."""

    @pytest.mark.asyncio
    async def test_react_mode_delegates_to_loop_runner(
        self,
        mock_brain: AsyncMock,
        mock_tools: dict[ToolType, AsyncMock],
        mock_skills: dict[SkillType, AsyncMock],
    ) -> None:
        config = CodeReviewerAgentConfig(
            priority_models=["openai:gpt-4o"],
            execution_mode=AgentExecutionMode.REACT_LOOP,
        )
        mock_workflow = AsyncMock()
        agent = CodeReviewerAgent(
            config=config,
            brain=mock_brain,
            tools=mock_tools,
            skills=mock_skills,
            deterministic_workflow=mock_workflow,
        )
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
    async def test_react_mode_does_not_call_workflow(
        self,
        mock_brain: AsyncMock,
        mock_tools: dict[ToolType, AsyncMock],
        mock_skills: dict[SkillType, AsyncMock],
    ) -> None:
        config = CodeReviewerAgentConfig(
            priority_models=["openai:gpt-4o"],
            execution_mode=AgentExecutionMode.REACT_LOOP,
        )
        mock_workflow = AsyncMock()
        agent = CodeReviewerAgent(
            config=config,
            brain=mock_brain,
            tools=mock_tools,
            skills=mock_skills,
            deterministic_workflow=mock_workflow,
        )
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

        mock_workflow.execute.assert_not_awaited()
