import logging
from collections.abc import Mapping
from typing import Any

from software_factory_poc.core.application.agents.common.base_agent import BaseAgent
from software_factory_poc.core.application.agents.loops.agentic_loop_runner import (
    AgenticLoopRunner,
)
from software_factory_poc.core.application.policies.tool_safety_policy import ToolSafetyPolicy
from software_factory_poc.core.application.ports import BrainPort
from software_factory_poc.core.application.skills.skill import BaseSkill
from software_factory_poc.core.application.workflows.base_workflow import BaseWorkflow
from software_factory_poc.core.domain.agent import (
    AgentExecutionMode,
    AgentIdentity,
    ScaffolderAgentConfig,
)
from software_factory_poc.core.domain.mission import Mission
from software_factory_poc.core.domain.shared.base_tool import BaseTool
from software_factory_poc.core.domain.shared.skill_type import SkillType
from software_factory_poc.core.domain.shared.tool_type import ToolType

logger = logging.getLogger(__name__)


class ScaffolderAgent(BaseAgent):
    """BrahMAS Scaffolder Agent — Dual-Flow (Deterministic + Agentic)."""

    def __init__(
        self,
        config: ScaffolderAgentConfig,
        brain: BrainPort,
        tools: Mapping[ToolType, BaseTool],
        skills: Mapping[SkillType, BaseSkill[Any, Any]],
        deterministic_workflow: BaseWorkflow,
    ):
        super().__init__(
            identity=AgentIdentity(
                name="ScaffolderAgent",
                role="Orchestrator",
                goal="Orchestrate scaffolding creation",
            ),
            config=config,
            brain=brain,
            tools=tools,
            skills=skills,
        )
        self._deterministic_workflow = deterministic_workflow
        self._loop_runner = AgenticLoopRunner(brain=self._brain, policy=ToolSafetyPolicy())

    async def run(self, mission: Mission) -> None:
        """Public entry point — dispatches to deterministic or agentic mode."""
        if self._execution_mode == AgentExecutionMode.REACT_LOOP:
            await self._run_agentic_loop(mission)
        else:
            await self._run_deterministic(mission)

    async def _run_deterministic(self, mission: Mission) -> None:
        """Delegate entirely to the extracted workflow."""
        await self._deterministic_workflow.execute(mission)

    async def _run_agentic_loop(self, mission: Mission) -> None:
        logger.info("[Scaffolder] Starting agentic loop for %s", mission.key)
        system_prompt = (
            "You are a scaffolding agent for BrahMAS.\n"
            "Your goal: create the project scaffolding, commit it to a branch, "
            "open a Merge Request, and report status to Jira.\n"
            "RULES:\n"
            "- Check if the branch already exists BEFORE creating it.\n"
            "- If the branch exists, report to Jira and STOP.\n"
            "- Never leak secrets or tokens in generated files.\n"
        )
        await self._loop_runner.run_loop(
            mission=mission,
            system_prompt=system_prompt,
            tools_registry=self._tools,
            priority_models=self._priority_models,
            max_iterations=self._config.max_iterations,
        )
