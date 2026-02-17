import logging
from typing import Any

from software_factory_poc.core.application.agents.code_reviewer.config.code_reviewer_agent_di_config import (
    CodeReviewerAgentConfig,
)
from software_factory_poc.core.application.agents.common.agent_execution_mode import (
    AgentExecutionMode,
)
from software_factory_poc.core.application.agents.common.agent_structures import AgentPorts
from software_factory_poc.core.application.agents.common.base_agent import AgentIdentity, BaseAgent
from software_factory_poc.core.application.agents.loops.agentic_loop_runner import (
    AgenticLoopRunner,
)
from software_factory_poc.core.application.skills.review.analyze_code_review_skill import (
    AnalyzeCodeReviewInput,
    AnalyzeCodeReviewSkill,
)
from software_factory_poc.core.application.skills.review.fetch_review_diff_skill import (
    FetchReviewDiffInput,
    FetchReviewDiffSkill,
)
from software_factory_poc.core.application.skills.review.publish_code_review_skill import (
    PublishCodeReviewInput,
    PublishCodeReviewSkill,
)
from software_factory_poc.core.application.skills.review.validate_review_context_skill import (
    ValidateReviewContextSkill,
)
from software_factory_poc.core.domain.mission import Mission

logger = logging.getLogger(__name__)


class CodeReviewerAgent(BaseAgent):
    """BrahMAS Code Reviewer Agent — Dual-Flow (Deterministic + Agentic)."""

    def __init__(
        self,
        config: CodeReviewerAgentConfig,
        ports: AgentPorts,
        validate_context: ValidateReviewContextSkill,
        fetch_diff: FetchReviewDiffSkill,
        analyze: AnalyzeCodeReviewSkill,
        publish: PublishCodeReviewSkill,
        loop_runner: AgenticLoopRunner,
    ):
        super().__init__(
            identity=AgentIdentity(
                name="CodeReviewerAgent",
                role="Reviewer",
                goal="Perform automated code reviews",
            ),
            brain=ports.brain,
            priority_models=config.priority_models,
            execution_mode=config.execution_mode,
        )
        self._config = config
        self._ports = ports
        self._validate_context = validate_context
        self._fetch_diff = fetch_diff
        self._analyze = analyze
        self._publish = publish
        self._loop_runner = loop_runner

    async def run(self, mission: Mission) -> None:
        """Public entry point — dispatches to deterministic or agentic mode."""
        if self._execution_mode == AgentExecutionMode.REACT_LOOP:
            await self._run_agentic_loop(mission)
        else:
            await self._run_deterministic(mission)

    async def _run_deterministic(self, mission: Mission) -> Any:
        logger.info("[Reviewer] Starting deterministic flow for %s", mission.key)

        ctx = await self._validate_context.execute(mission)

        diff_output = await self._fetch_diff.execute(
            FetchReviewDiffInput(mr_iid=ctx.mr_iid, context_query=mission.summary),
        )

        report = await self._analyze.execute(
            AnalyzeCodeReviewInput(
                mission_summary=mission.summary,
                mission_description=mission.description.raw_content,
                mr_diff=diff_output.mr_diff,
                conventions=diff_output.conventions,
                priority_models=self._priority_models,
            ),
        )

        await self._publish.execute(
            PublishCodeReviewInput(
                mission_key=mission.key,
                mr_iid=ctx.mr_iid,
                mr_url=ctx.mr_url,
                report=report,
            ),
        )

        logger.info("[Reviewer] %s completed", mission.key)

    async def _run_agentic_loop(self, mission: Mission) -> None:
        logger.info("[Reviewer] Starting agentic loop for %s", mission.key)

        vcs_tools = await self._ports.vcs.get_mcp_tools()
        tracker_tools = await self._ports.tracker.get_mcp_tools()
        docs_tools = await self._ports.docs.get_mcp_tools()
        all_tools = vcs_tools + tracker_tools + docs_tools

        async def _tool_executor(tool_name: str, arguments: dict[str, Any]) -> str:
            if tool_name.startswith("vcs_"):
                return str(await self._ports.vcs.execute_tool(tool_name, arguments))
            if tool_name.startswith("tracker_"):
                return str(await self._ports.tracker.execute_tool(tool_name, arguments))
            if tool_name.startswith("docs_"):
                return str(await self._ports.docs.execute_tool(tool_name, arguments))
            return f"Error: unknown tool prefix for '{tool_name}'"

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
            available_tools=all_tools,
            tool_executor=_tool_executor,
            priority_models=self._priority_models,
            max_iterations=self._config.max_iterations,
        )
