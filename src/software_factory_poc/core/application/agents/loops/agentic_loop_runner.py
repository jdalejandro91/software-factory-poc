from collections.abc import Mapping
from typing import Any

import structlog

from software_factory_poc.core.application.policies.tool_safety_policy import ToolSafetyPolicy
from software_factory_poc.core.application.ports import BrainPort
from software_factory_poc.core.domain.mission import Mission
from software_factory_poc.core.domain.shared.base_tool import BaseTool
from software_factory_poc.core.domain.shared.tool_type import ToolType

logger = structlog.get_logger()


class AgenticLoopRunner:
    """Pure-Python ReAct loop engine.

    Drives a Think -> Act -> Observe cycle using ``BrainPort.generate_with_tools``
    and an auto-discovered tool registry.  A ``ToolSafetyPolicy``
    gates which tools are exposed to the LLM.
    """

    def __init__(self, brain: BrainPort, policy: ToolSafetyPolicy) -> None:
        self._brain = brain
        self._policy = policy

    async def run_loop(
        self,
        mission: Mission,
        system_prompt: str,
        tools_registry: Mapping[ToolType, BaseTool],
        priority_models: list[str],
        max_iterations: int = 5,
    ) -> str:
        """Execute a ReAct loop until the LLM stops calling tools or the limit is reached."""
        safe_tools, name_to_tool = await self._prepare_tool_schemas(tools_registry)
        messages = self._build_initial_messages(system_prompt, mission)
        for iteration in range(1, max_iterations + 1):
            logger.info(
                "Agentic loop iteration",
                iteration=iteration,
                max_iterations=max_iterations,
                issue_key=mission.key,
            )
            response = await self._brain.generate_with_tools(
                messages=messages, tools=safe_tools, priority_models=priority_models
            )
            tool_calls: list[dict[str, Any]] = response.get("tool_calls", [])
            if not tool_calls:
                return str(response.get("content", ""))
            await self._process_tool_calls(messages, response, tool_calls, name_to_tool)
        logger.warning(
            "Max iterations reached", max_iterations=max_iterations, issue_key=mission.key
        )
        return str(messages[-1].get("content", ""))

    async def _prepare_tool_schemas(
        self, tools_registry: Mapping[ToolType, BaseTool]
    ) -> tuple[list[dict[str, Any]], dict[str, BaseTool]]:
        """Gather MCP schemas and apply safety policy filtering."""
        all_schemas, name_to_tool = await self._gather_tools(tools_registry)
        safe_tools = self._policy.filter_allowed_tools(all_schemas, agent_role="default")
        return safe_tools, name_to_tool

    @staticmethod
    def _build_initial_messages(system_prompt: str, mission: Mission) -> list[dict[str, Any]]:
        """Construct the initial messages array for the ReAct loop."""
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": AgenticLoopRunner._build_user_message(mission)},
        ]

    @staticmethod
    async def _process_tool_calls(
        messages: list[dict[str, Any]],
        response: dict[str, Any],
        tool_calls: list[dict[str, Any]],
        name_to_tool: dict[str, BaseTool],
    ) -> None:
        """Append the assistant message and execute each tool call."""
        messages.append(
            {"role": "assistant", "content": response.get("content", ""), "tool_calls": tool_calls}
        )
        for tool_call in tool_calls:
            fn = tool_call.get("function", {})
            result = await AgenticLoopRunner._execute_tool_safely(
                name_to_tool, fn.get("name", ""), fn.get("arguments", {})
            )
            messages.append(
                {"role": "tool", "tool_call_id": tool_call.get("id", ""), "content": result}
            )

    @staticmethod
    def _build_user_message(mission: Mission) -> str:
        """Build user message with XML-delimited Jira data to prevent prompt injection."""
        return (
            f"Mission {mission.key} ({mission.issue_type})\n\n"
            f"<jira_summary>{mission.summary}</jira_summary>\n\n"
            f"<jira_description>{mission.description.raw_content}</jira_description>"
        )

    @staticmethod
    async def _gather_tools(
        tools_registry: Mapping[ToolType, BaseTool],
    ) -> tuple[list[dict[str, Any]], dict[str, BaseTool]]:
        """Collect MCP schemas from every tool and build a name-to-tool routing map."""
        all_schemas: list[dict[str, Any]] = []
        name_to_tool: dict[str, BaseTool] = {}
        for tool in tools_registry.values():
            schemas = await tool.get_mcp_tools()
            for schema in schemas:
                fn_name = schema.get("function", {}).get("name", "")
                if fn_name:
                    name_to_tool[fn_name] = tool
            all_schemas.extend(schemas)
        return all_schemas, name_to_tool

    @staticmethod
    async def _execute_tool_safely(
        name_to_tool: dict[str, BaseTool],
        tool_name: str,
        tool_args: dict[str, Any],
    ) -> str:
        """Route the call to the correct tool adapter, catching errors."""
        try:
            tool = name_to_tool.get(tool_name)
            if tool is None:
                logger.warning(
                    "Unknown tool requested",
                    tool_name=tool_name,
                    available_tools=list(name_to_tool.keys()),
                )
                return f"Error: unknown tool '{tool_name}'"
            return str(await tool.execute_tool(tool_name, tool_args))
        except Exception as exc:
            logger.exception(
                "Tool execution failed",
                tool_name=tool_name,
                error_type=type(exc).__name__,
                error_details=str(exc),
            )
            return f"Error: Tool execution failed — {type(exc).__name__}: {exc}"
