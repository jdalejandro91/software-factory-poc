"""Unit tests — ScaffolderAgent dual-flow delegation (zero I/O, workflow mocked)."""

from unittest.mock import AsyncMock

import pytest

from software_factory_poc.core.application.agents.common.agent_config import (
    ScaffolderAgentConfig,
)
from software_factory_poc.core.application.agents.common.agent_execution_mode import (
    AgentExecutionMode,
)
from software_factory_poc.core.application.agents.scaffolder.scaffolder_agent import ScaffolderAgent
from software_factory_poc.core.domain.mission import Mission, TaskDescription
from software_factory_poc.core.domain.shared.skill_type import SkillType
from software_factory_poc.core.domain.shared.tool_type import ToolType

# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture()
def agent_config() -> ScaffolderAgentConfig:
    return ScaffolderAgentConfig(priority_models=["openai:gpt-4o"])


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
    return {SkillType.GENERATE_SCAFFOLD_PLAN: AsyncMock()}


@pytest.fixture()
def mock_workflow() -> AsyncMock:
    return AsyncMock()


@pytest.fixture()
def agent(
    agent_config: ScaffolderAgentConfig,
    mock_brain: AsyncMock,
    mock_tools: dict[ToolType, AsyncMock],
    mock_skills: dict[SkillType, AsyncMock],
    mock_workflow: AsyncMock,
) -> ScaffolderAgent:
    return ScaffolderAgent(
        config=agent_config,
        brain=mock_brain,
        tools=mock_tools,
        skills=mock_skills,
        deterministic_workflow=mock_workflow,
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


# ══════════════════════════════════════════════════════════════════════
# Deterministic Delegation
# ══════════════════════════════════════════════════════════════════════


class TestDeterministicDelegation:
    """Verify the agent delegates deterministic mode to the workflow."""

    @pytest.mark.asyncio
    async def test_deterministic_mode_delegates_to_workflow(
        self,
        agent: ScaffolderAgent,
        mock_workflow: AsyncMock,
        mission: Mission,
    ) -> None:
        await agent.run(mission)

        mock_workflow.execute.assert_awaited_once_with(mission)

    @pytest.mark.asyncio
    async def test_workflow_error_propagates(
        self,
        agent: ScaffolderAgent,
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
    """Verify the agent correctly delegates to the loop runner in REACT_LOOP mode."""

    @pytest.mark.asyncio
    async def test_react_mode_delegates_to_loop_runner(
        self,
        mock_brain: AsyncMock,
        mock_tools: dict[ToolType, AsyncMock],
        mock_skills: dict[SkillType, AsyncMock],
    ) -> None:
        config = ScaffolderAgentConfig(
            priority_models=["openai:gpt-4o"],
            execution_mode=AgentExecutionMode.REACT_LOOP,
        )
        mock_workflow = AsyncMock()
        agent = ScaffolderAgent(
            config=config,
            brain=mock_brain,
            tools=mock_tools,
            skills=mock_skills,
            deterministic_workflow=mock_workflow,
        )
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
    async def test_react_mode_does_not_call_workflow(
        self,
        mock_brain: AsyncMock,
        mock_tools: dict[ToolType, AsyncMock],
        mock_skills: dict[SkillType, AsyncMock],
    ) -> None:
        config = ScaffolderAgentConfig(
            priority_models=["openai:gpt-4o"],
            execution_mode=AgentExecutionMode.REACT_LOOP,
        )
        mock_workflow = AsyncMock()
        agent = ScaffolderAgent(
            config=config,
            brain=mock_brain,
            tools=mock_tools,
            skills=mock_skills,
            deterministic_workflow=mock_workflow,
        )
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

        mock_workflow.execute.assert_not_awaited()
