"""Unit tests — ScaffolderAgent dual-flow (zero I/O, all Skills mocked)."""

from unittest.mock import AsyncMock

import pytest

from software_factory_poc.core.application.agents.common.agent_execution_mode import (
    AgentExecutionMode,
)
from software_factory_poc.core.application.agents.common.agent_structures import AgentPorts
from software_factory_poc.core.application.agents.scaffolder.config.scaffolder_agent_di_config import (
    ScaffolderAgentConfig,
)
from software_factory_poc.core.application.agents.scaffolder.contracts.scaffolder_contracts import (
    FileSchemaDTO,
    ScaffoldingResponseSchema,
)
from software_factory_poc.core.application.agents.scaffolder.scaffolder_agent import ScaffolderAgent
from software_factory_poc.core.application.skills.scaffold.apply_scaffold_delivery_skill import (
    ApplyScaffoldDeliveryInput,
)
from software_factory_poc.core.application.skills.scaffold.generate_scaffold_plan_skill import (
    GenerateScaffoldPlanInput,
)
from software_factory_poc.core.application.skills.scaffold.report_success_skill import (
    ReportSuccessInput,
)
from software_factory_poc.core.domain.mission import Mission, TaskDescription

# ── Helpers ──


def _make_mission(key: str = "PROJ-100", service_name: str = "my-service") -> Mission:
    return Mission(
        id="10001",
        key=key,
        summary="Create microservice scaffolding",
        status="To Do",
        project_key="PROJ",
        issue_type="Task",
        description=TaskDescription(
            raw_content="Create scaffolding for my-service",
            config={
                "parameters": {"service_name": service_name},
                "target": {
                    "gitlab_project_id": "42",
                    "default_branch": "main",
                },
            },
        ),
    )


def _make_scaffold_plan() -> ScaffoldingResponseSchema:
    return ScaffoldingResponseSchema(
        branch_name="feature/proj-100-my-service",
        commit_message="feat: scaffold my-service",
        files=[
            FileSchemaDTO(path="src/main.py", content="print('hello')", is_new=True),
        ],
    )


def _build_agent(
    execution_mode: AgentExecutionMode = AgentExecutionMode.DETERMINISTIC,
) -> tuple[ScaffolderAgent, dict[str, AsyncMock]]:
    """Build a ScaffolderAgent with all dependencies mocked."""
    mocks = {
        "vcs": AsyncMock(),
        "tracker": AsyncMock(),
        "docs": AsyncMock(),
        "brain": AsyncMock(),
        "idempotency_check": AsyncMock(),
        "fetch_context": AsyncMock(),
        "generate_plan": AsyncMock(),
        "apply_delivery": AsyncMock(),
        "report_success": AsyncMock(),
        "loop_runner": AsyncMock(),
    }

    agent = ScaffolderAgent(
        config=ScaffolderAgentConfig(
            priority_models=["openai:gpt-4o"],
            execution_mode=execution_mode,
        ),
        ports=AgentPorts(
            vcs=mocks["vcs"],
            tracker=mocks["tracker"],
            docs=mocks["docs"],
            brain=mocks["brain"],
        ),
        idempotency_check=mocks["idempotency_check"],
        fetch_context=mocks["fetch_context"],
        generate_plan=mocks["generate_plan"],
        apply_delivery=mocks["apply_delivery"],
        report_success=mocks["report_success"],
        loop_runner=mocks["loop_runner"],
    )
    return agent, mocks


# ══════════════════════════════════════════════════════════════════════
# Deterministic Pipeline
# ══════════════════════════════════════════════════════════════════════


class TestDeterministicPipeline:
    """Verify the agent orchestrates the 5-skill pipeline in order."""

    async def test_full_pipeline_calls_all_skills_in_order(self) -> None:
        agent, mocks = _build_agent()
        mission = _make_mission()
        plan = _make_scaffold_plan()

        mocks["idempotency_check"].execute.return_value = False
        mocks["fetch_context"].execute.return_value = "arch context"
        mocks["generate_plan"].execute.return_value = plan
        mocks["apply_delivery"].execute.return_value = "https://gitlab.com/mr/1"
        mocks["report_success"].execute.return_value = None

        await agent.run(mission)

        mocks["idempotency_check"].execute.assert_awaited_once()
        mocks["fetch_context"].execute.assert_awaited_once_with("my-service")
        mocks["generate_plan"].execute.assert_awaited_once()
        mocks["apply_delivery"].execute.assert_awaited_once()
        mocks["report_success"].execute.assert_awaited_once()

    async def test_idempotency_abort_skips_remaining_skills(self) -> None:
        agent, mocks = _build_agent()
        mission = _make_mission()

        mocks["idempotency_check"].execute.return_value = True

        await agent.run(mission)

        mocks["idempotency_check"].execute.assert_awaited_once()
        mocks["fetch_context"].execute.assert_not_awaited()
        mocks["generate_plan"].execute.assert_not_awaited()
        mocks["apply_delivery"].execute.assert_not_awaited()
        mocks["report_success"].execute.assert_not_awaited()

    async def test_generate_plan_receives_correct_input(self) -> None:
        agent, mocks = _build_agent()
        mission = _make_mission()
        plan = _make_scaffold_plan()

        mocks["idempotency_check"].execute.return_value = False
        mocks["fetch_context"].execute.return_value = "arch context"
        mocks["generate_plan"].execute.return_value = plan
        mocks["apply_delivery"].execute.return_value = "https://gitlab.com/mr/1"

        await agent.run(mission)

        call_args = mocks["generate_plan"].execute.call_args[0][0]
        assert isinstance(call_args, GenerateScaffoldPlanInput)
        assert call_args.mission is mission
        assert call_args.arch_context == "arch context"
        assert call_args.priority_models == ["openai:gpt-4o"]

    async def test_apply_delivery_receives_correct_input(self) -> None:
        agent, mocks = _build_agent()
        mission = _make_mission()
        plan = _make_scaffold_plan()

        mocks["idempotency_check"].execute.return_value = False
        mocks["fetch_context"].execute.return_value = "arch"
        mocks["generate_plan"].execute.return_value = plan
        mocks["apply_delivery"].execute.return_value = "https://gitlab.com/mr/1"

        await agent.run(mission)

        call_args = mocks["apply_delivery"].execute.call_args[0][0]
        assert isinstance(call_args, ApplyScaffoldDeliveryInput)
        assert call_args.mission_key == "PROJ-100"
        assert call_args.target_branch == "main"
        assert call_args.scaffold_plan is plan

    async def test_report_success_receives_correct_input(self) -> None:
        agent, mocks = _build_agent()
        mission = _make_mission()
        plan = _make_scaffold_plan()

        mocks["idempotency_check"].execute.return_value = False
        mocks["fetch_context"].execute.return_value = "arch"
        mocks["generate_plan"].execute.return_value = plan
        mocks["apply_delivery"].execute.return_value = "https://gitlab.com/mr/1"

        await agent.run(mission)

        call_args = mocks["report_success"].execute.call_args[0][0]
        assert isinstance(call_args, ReportSuccessInput)
        assert call_args.mr_url == "https://gitlab.com/mr/1"
        assert call_args.gitlab_project_id == "42"
        assert call_args.files_count == 1

    async def test_skill_failure_propagates(self) -> None:
        agent, mocks = _build_agent()
        mission = _make_mission()

        mocks["idempotency_check"].execute.return_value = False
        mocks["fetch_context"].execute.side_effect = RuntimeError("Confluence down")

        with pytest.raises(RuntimeError, match="Confluence down"):
            await agent.run(mission)


# ══════════════════════════════════════════════════════════════════════
# Agentic Routing
# ══════════════════════════════════════════════════════════════════════


class TestAgenticRouting:
    """Verify the agent correctly delegates to the loop runner in REACT_LOOP mode."""

    async def test_react_mode_delegates_to_loop_runner(self) -> None:
        agent, mocks = _build_agent(execution_mode=AgentExecutionMode.REACT_LOOP)
        mission = _make_mission()

        mocks["vcs"].get_mcp_tools.return_value = [
            {"type": "function", "function": {"name": "vcs_create_branch"}}
        ]
        mocks["tracker"].get_mcp_tools.return_value = [
            {"type": "function", "function": {"name": "tracker_add_comment"}}
        ]
        mocks["docs"].get_mcp_tools.return_value = []
        mocks["loop_runner"].run_loop.return_value = "done"

        await agent.run(mission)

        mocks["loop_runner"].run_loop.assert_awaited_once()
        call_kwargs = mocks["loop_runner"].run_loop.call_args[1]
        assert call_kwargs["mission"] is mission
        assert len(call_kwargs["available_tools"]) == 2
        assert call_kwargs["priority_models"] == ["openai:gpt-4o"]

    async def test_react_mode_does_not_call_deterministic_skills(self) -> None:
        agent, mocks = _build_agent(execution_mode=AgentExecutionMode.REACT_LOOP)
        mission = _make_mission()

        mocks["vcs"].get_mcp_tools.return_value = []
        mocks["tracker"].get_mcp_tools.return_value = []
        mocks["docs"].get_mcp_tools.return_value = []
        mocks["loop_runner"].run_loop.return_value = "done"

        await agent.run(mission)

        mocks["idempotency_check"].execute.assert_not_awaited()
        mocks["fetch_context"].execute.assert_not_awaited()
        mocks["generate_plan"].execute.assert_not_awaited()
        mocks["apply_delivery"].execute.assert_not_awaited()
        mocks["report_success"].execute.assert_not_awaited()
