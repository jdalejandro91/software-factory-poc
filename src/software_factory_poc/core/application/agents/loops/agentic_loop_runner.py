import logging
from collections.abc import Callable, Coroutine
from typing import Any

from software_factory_poc.core.application.policies.tool_safety_policy import ToolSafetyPolicy
from software_factory_poc.core.application.ports.brain_port import BrainPort
from software_factory_poc.core.domain.mission.entities.mission import Mission

logger = logging.getLogger(__name__)

ToolExecutor = Callable[[str, dict[str, Any]], Coroutine[Any, Any, str]]


class AgenticLoopRunner:
    """Pure-Python ReAct loop engine.

    Drives a Think → Act → Observe cycle using ``BrainPort.generate_with_tools``
    and an externally-provided ``tool_executor`` callback.  A ``ToolSafetyPolicy``
    gates which tools are exposed to the LLM.
    """

    def __init__(self, brain: BrainPort, policy: ToolSafetyPolicy) -> None:
        self._brain = brain
        self._policy = policy

    async def run_loop(
        self,
        mission: Mission,
        system_prompt: str,
        available_tools: list[dict[str, Any]],
        tool_executor: ToolExecutor,
        priority_models: list[str],
        max_iterations: int = 5,
    ) -> str:
        """Execute a ReAct loop until the LLM stops calling tools or the limit is reached.

        Args:
            mission: The domain mission driving this loop.
            system_prompt: System-level instructions for the LLM.
            available_tools: OpenAI-compatible tool definitions (pre-filtered by caller).
            tool_executor: ``async (tool_name, arguments) -> result_str`` callback.
            priority_models: Ordered model identifiers for fallback.
            max_iterations: Safety cap to prevent runaway loops.

        Returns:
            The final textual response from the LLM.
        """
        safe_tools = self._policy.filter_allowed_tools(available_tools, agent_role="default")

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"Mission: {mission.summary}\n\n{mission.description.raw_content}",
            },
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
                    tool_executor,
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
    async def _execute_tool_safely(
        executor: ToolExecutor,
        tool_name: str,
        tool_args: dict[str, Any],
    ) -> str:
        """Invoke the tool executor, catching errors so the LLM can self-correct."""
        try:
            return await executor(tool_name, tool_args)
        except Exception as exc:
            logger.warning("[AgenticLoop] Tool '%s' failed: %s", tool_name, exc)
            return f"Error: Tool execution failed — {exc}"
