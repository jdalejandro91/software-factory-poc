import logging
from collections.abc import Mapping
from typing import Any

from software_factory_poc.core.application.policies.tool_safety_policy import ToolSafetyPolicy
from software_factory_poc.core.application.ports import BrainPort
from software_factory_poc.core.domain.mission import Mission
from software_factory_poc.core.domain.shared.base_tool import BaseTool
from software_factory_poc.core.domain.shared.tool_type import ToolType

logger = logging.getLogger(__name__)


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
        """Execute a ReAct loop until the LLM stops calling tools or the limit is reached.

        Args:
            mission: The domain mission driving this loop.
            system_prompt: System-level instructions for the LLM.
            tools_registry: Map of ToolType -> BaseTool; MCP schemas are auto-gathered.
            priority_models: Ordered model identifiers for fallback.
            max_iterations: Safety cap to prevent runaway loops.

        Returns:
            The final textual response from the LLM.
        """
        all_schemas, name_to_tool = await self._gather_tools(tools_registry)
        safe_tools = self._policy.filter_allowed_tools(all_schemas, agent_role="default")

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": self._build_user_message(mission)},
        ]

        for iteration in range(1, max_iterations + 1):
            logger.info(
                "[AgenticLoop] Iteration %d/%d for %s", iteration, max_iterations, mission.key
            )

            response = await self._brain.generate_with_tools(
                messages=messages,
                tools=safe_tools,
                priority_models=priority_models,
            )

            tool_calls: list[dict[str, Any]] = response.get("tool_calls", [])

            if not tool_calls:
                return str(response.get("content", ""))

            messages.append(
                {
                    "role": "assistant",
                    "content": response.get("content", ""),
                    "tool_calls": tool_calls,
                },
            )

            for tool_call in tool_calls:
                fn = tool_call.get("function", {})
                tool_name: str = fn.get("name", "")
                tool_args: dict[str, Any] = fn.get("arguments", {})
                call_id: str = tool_call.get("id", "")

                result = await self._execute_tool_safely(
                    name_to_tool,
                    tool_name,
                    tool_args,
                )
                messages.append(
                    {"role": "tool", "tool_call_id": call_id, "content": result},
                )

        logger.warning(
            "[AgenticLoop] Max iterations (%d) reached for %s",
            max_iterations,
            mission.key,
        )
        return str(messages[-1].get("content", ""))

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
                    "[AgenticLoop] Unknown tool requested: '%s' (available: %s)",
                    tool_name,
                    list(name_to_tool.keys()),
                )
                return f"Error: unknown tool '{tool_name}'"
            return str(await tool.execute_tool(tool_name, tool_args))
        except Exception as exc:
            logger.exception(
                "[AgenticLoop] Tool '%s' failed: %s (args=%s)", tool_name, exc, tool_args
            )
            return f"Error: Tool execution failed — {type(exc).__name__}: {exc}"
