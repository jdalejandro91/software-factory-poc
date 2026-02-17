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
    CodeReviewerAgentConfig,
)
from software_factory_poc.core.domain.mission import Mission
from software_factory_poc.core.domain.shared.base_tool import BaseTool
from software_factory_poc.core.domain.shared.skill_type import SkillType
from software_factory_poc.core.domain.shared.tool_type import ToolType

logger = logging.getLogger(__name__)


class CodeReviewerAgent(BaseAgent):
    """BrahMAS Code Reviewer Agent — Dual-Flow (Deterministic + Agentic)."""

    def __init__(
        self,
        config: CodeReviewerAgentConfig,
        brain: BrainPort,
        tools: Mapping[ToolType, BaseTool],
        skills: Mapping[SkillType, BaseSkill[Any, Any]],
        deterministic_workflow: BaseWorkflow,
    ):
        super().__init__(
            identity=AgentIdentity(
                name="CodeReviewerAgent",
                role="Reviewer",
                goal="Perform automated code reviews",
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
        logger.info("[Reviewer] Starting agentic loop for %s", mission.key)
        system_prompt = (
            "You are a code review agent for BrahMAS.\n"
            "Your goal: review the Merge Request diff, produce a structured CodeReviewReport, "
            "publish the review to GitLab, and report status to Jira.\n"
            "RULES:\n"
            "- Never approve code with CRITICAL security issues.\n"
            "- Never merge or delete branches.\n"
            "- Never leak secrets or tokens.\n"
        )
        await self._loop_runner.run_loop(
            mission=mission,
            system_prompt=system_prompt,
            tools_registry=self._tools,
            priority_models=self._priority_models,
            max_iterations=self._config.max_iterations,
        )
