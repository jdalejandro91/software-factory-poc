"""Unit tests — AgenticLoopRunner (zero I/O, Brain + Policy mocked)."""

from typing import cast
from unittest.mock import AsyncMock, MagicMock

import pytest

from software_factory_poc.core.application.agents.loops.agentic_loop_runner import (
    AgenticLoopRunner,
)
from software_factory_poc.core.application.policies.tool_safety_policy import ToolSafetyPolicy
from software_factory_poc.core.domain.mission import Mission, TaskDescription
from software_factory_poc.core.domain.shared.base_tool import BaseTool
from software_factory_poc.core.domain.shared.tool_type import ToolType

# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture()
def mock_brain() -> AsyncMock:
    return AsyncMock()


@pytest.fixture()
def mock_policy() -> MagicMock:
    policy = MagicMock(spec=ToolSafetyPolicy)
    policy.filter_allowed_tools.side_effect = lambda tools, **_: tools
    return policy


@pytest.fixture()
def runner(mock_brain: AsyncMock, mock_policy: MagicMock) -> AgenticLoopRunner:
    return AgenticLoopRunner(brain=mock_brain, policy=mock_policy)


@pytest.fixture()
def mission() -> Mission:
    return Mission(
        id="30001",
        key="LOOP-1",
        summary="Test ReAct loop",
        status="To Do",
        project_key="LOOP",
        issue_type="Task",
        description=TaskDescription(raw_content="Run the loop", config={}),
    )


@pytest.fixture()
def tools_registry() -> dict[ToolType, AsyncMock]:
    vcs = AsyncMock()
    vcs.get_mcp_tools.return_value = [
        {"function": {"name": "create_branch", "parameters": {}}, "type": "function"}
    ]
    tracker = AsyncMock()
    tracker.get_mcp_tools.return_value = [
        {"function": {"name": "add_comment", "parameters": {}}, "type": "function"}
    ]
    return {ToolType.VCS: vcs, ToolType.TRACKER: tracker}


# ══════════════════════════════════════════════════════════════════════
# _gather_tools
# ══════════════════════════════════════════════════════════════════════


class TestGatherTools:
    """Verify tool discovery from registry."""

    @pytest.mark.asyncio
    async def test_collects_all_schemas(self, tools_registry: dict[ToolType, AsyncMock]) -> None:
        schemas, name_map = await AgenticLoopRunner._gather_tools(tools_registry)

        assert len(schemas) == 2
        assert "create_branch" in name_map
        assert "add_comment" in name_map

    @pytest.mark.asyncio
    async def test_maps_tool_name_to_correct_adapter(
        self, tools_registry: dict[ToolType, AsyncMock]
    ) -> None:
        _, name_map = await AgenticLoopRunner._gather_tools(tools_registry)

        assert name_map["create_branch"] is tools_registry[ToolType.VCS]
        assert name_map["add_comment"] is tools_registry[ToolType.TRACKER]

    @pytest.mark.asyncio
    async def test_skips_schemas_without_function_name(self) -> None:
        tool = AsyncMock()
        tool.get_mcp_tools.return_value = [{"function": {}, "type": "function"}]
        registry = {ToolType.VCS: tool}

        schemas, name_map = await AgenticLoopRunner._gather_tools(registry)

        assert len(schemas) == 1
        assert len(name_map) == 0

    @pytest.mark.asyncio
    async def test_empty_registry_returns_empty(self) -> None:
        schemas, name_map = await AgenticLoopRunner._gather_tools({})

        assert schemas == []
        assert name_map == {}


# ══════════════════════════════════════════════════════════════════════
# _execute_tool_safely
# ══════════════════════════════════════════════════════════════════════


class TestExecuteToolSafely:
    """Verify tool execution routing and error handling."""

    @pytest.mark.asyncio
    async def test_routes_to_correct_tool(self) -> None:
        tool = AsyncMock()
        tool.execute_tool.return_value = "branch created"
        name_map: dict[str, BaseTool] = {"create_branch": cast(BaseTool, tool)}

        result = await AgenticLoopRunner._execute_tool_safely(
            name_map, "create_branch", {"name": "feature/x"}
        )

        assert result == "branch created"
        tool.execute_tool.assert_awaited_once_with("create_branch", {"name": "feature/x"})

    @pytest.mark.asyncio
    async def test_returns_error_for_unknown_tool(self) -> None:
        empty_map: dict[str, BaseTool] = {}
        result = await AgenticLoopRunner._execute_tool_safely(empty_map, "unknown_tool", {})

        assert "unknown tool" in result.lower()

    @pytest.mark.asyncio
    async def test_catches_execution_exception(self) -> None:
        tool = AsyncMock()
        tool.execute_tool.side_effect = RuntimeError("connection lost")
        name_map: dict[str, BaseTool] = {"create_branch": cast(BaseTool, tool)}

        result = await AgenticLoopRunner._execute_tool_safely(name_map, "create_branch", {})

        assert "Error" in result
        assert "connection lost" in result


# ══════════════════════════════════════════════════════════════════════
# run_loop
# ══════════════════════════════════════════════════════════════════════


class TestRunLoop:
    """Verify the ReAct loop orchestration."""

    @pytest.mark.asyncio
    async def test_returns_content_when_no_tool_calls(
        self,
        runner: AgenticLoopRunner,
        mock_brain: AsyncMock,
        mission: Mission,
        tools_registry: dict[ToolType, AsyncMock],
    ) -> None:
        mock_brain.generate_with_tools.return_value = {
            "content": "All done, no tools needed.",
            "tool_calls": [],
        }

        result = await runner.run_loop(
            mission=mission,
            system_prompt="You are an agent.",
            tools_registry=tools_registry,
            priority_models=["openai:gpt-4o"],
        )

        assert result == "All done, no tools needed."
        mock_brain.generate_with_tools.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_executes_tool_calls_and_loops(
        self,
        runner: AgenticLoopRunner,
        mock_brain: AsyncMock,
        mission: Mission,
        tools_registry: dict[ToolType, AsyncMock],
    ) -> None:
        tools_registry[ToolType.VCS].execute_tool.return_value = "branch ok"

        mock_brain.generate_with_tools.side_effect = [
            {
                "content": "I need to create a branch.",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "function": {"name": "create_branch", "arguments": {"name": "feat/x"}},
                    }
                ],
            },
            {
                "content": "Branch created. Done.",
                "tool_calls": [],
            },
        ]

        result = await runner.run_loop(
            mission=mission,
            system_prompt="You are an agent.",
            tools_registry=tools_registry,
            priority_models=["openai:gpt-4o"],
        )

        assert result == "Branch created. Done."
        assert mock_brain.generate_with_tools.call_count == 2
        tools_registry[ToolType.VCS].execute_tool.assert_awaited_once_with(
            "create_branch", {"name": "feat/x"}
        )

    @pytest.mark.asyncio
    async def test_respects_max_iterations(
        self,
        runner: AgenticLoopRunner,
        mock_brain: AsyncMock,
        mission: Mission,
        tools_registry: dict[ToolType, AsyncMock],
    ) -> None:
        tools_registry[ToolType.VCS].execute_tool.return_value = "ok"

        mock_brain.generate_with_tools.return_value = {
            "content": "Still working...",
            "tool_calls": [
                {
                    "id": "call_n",
                    "function": {"name": "create_branch", "arguments": {}},
                }
            ],
        }

        await runner.run_loop(
            mission=mission,
            system_prompt="You are an agent.",
            tools_registry=tools_registry,
            priority_models=["openai:gpt-4o"],
            max_iterations=2,
        )

        assert mock_brain.generate_with_tools.call_count == 2

    @pytest.mark.asyncio
    async def test_policy_filters_tools(
        self,
        runner: AgenticLoopRunner,
        mock_brain: AsyncMock,
        mock_policy: MagicMock,
        mission: Mission,
        tools_registry: dict[ToolType, AsyncMock],
    ) -> None:
        mock_brain.generate_with_tools.return_value = {
            "content": "Done.",
            "tool_calls": [],
        }

        await runner.run_loop(
            mission=mission,
            system_prompt="You are an agent.",
            tools_registry=tools_registry,
            priority_models=["openai:gpt-4o"],
        )

        mock_policy.filter_allowed_tools.assert_called_once()
        filtered_schemas = mock_policy.filter_allowed_tools.call_args[0][0]
        assert len(filtered_schemas) == 2

    @pytest.mark.asyncio
    async def test_multiple_tool_calls_in_single_iteration(
        self,
        runner: AgenticLoopRunner,
        mock_brain: AsyncMock,
        mission: Mission,
        tools_registry: dict[ToolType, AsyncMock],
    ) -> None:
        tools_registry[ToolType.VCS].execute_tool.return_value = "branch ok"
        tools_registry[ToolType.TRACKER].execute_tool.return_value = "comment added"

        mock_brain.generate_with_tools.side_effect = [
            {
                "content": "I'll create a branch and add a comment.",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "function": {"name": "create_branch", "arguments": {"name": "feat/x"}},
                    },
                    {
                        "id": "call_2",
                        "function": {"name": "add_comment", "arguments": {"text": "started"}},
                    },
                ],
            },
            {
                "content": "All done.",
                "tool_calls": [],
            },
        ]

        result = await runner.run_loop(
            mission=mission,
            system_prompt="You are an agent.",
            tools_registry=tools_registry,
            priority_models=["openai:gpt-4o"],
        )

        assert result == "All done."
        tools_registry[ToolType.VCS].execute_tool.assert_awaited_once()
        tools_registry[ToolType.TRACKER].execute_tool.assert_awaited_once()
