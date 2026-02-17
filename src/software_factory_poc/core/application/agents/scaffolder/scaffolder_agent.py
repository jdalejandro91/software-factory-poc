import logging
from typing import Any

from software_factory_poc.core.application.agents.common.agent_execution_mode import (
    AgentExecutionMode,
)
from software_factory_poc.core.application.agents.common.base_agent import AgentIdentity, BaseAgent
from software_factory_poc.core.application.agents.loops.agentic_loop_runner import (
    AgenticLoopRunner,
)
from software_factory_poc.core.application.ports.brain_port import BrainPort
from software_factory_poc.core.application.ports.docs_port import DocsPort
from software_factory_poc.core.application.ports.tracker_port import TrackerPort
from software_factory_poc.core.application.ports.vcs_port import VcsPort
from software_factory_poc.core.application.skills.scaffold.apply_scaffold_delivery_skill import (
    ApplyScaffoldDeliveryInput,
    ApplyScaffoldDeliverySkill,
)
from software_factory_poc.core.application.skills.scaffold.fetch_scaffold_context_skill import (
    FetchScaffoldContextSkill,
)
from software_factory_poc.core.application.skills.scaffold.generate_scaffold_plan_skill import (
    GenerateScaffoldPlanInput,
    GenerateScaffoldPlanSkill,
)
from software_factory_poc.core.application.skills.scaffold.idempotency_check_skill import (
    IdempotencyCheckInput,
    IdempotencyCheckSkill,
)
from software_factory_poc.core.application.skills.scaffold.report_success_skill import (
    ReportSuccessInput,
    ReportSuccessSkill,
)
from software_factory_poc.core.domain.mission.entities.mission import Mission

logger = logging.getLogger(__name__)


class ScaffolderAgent(BaseAgent):
    """BrahMAS Scaffolder Agent — Dual-Flow (Deterministic + Agentic).

    Deterministic mode orchestrates injected Skills sequentially.
    Agentic mode delegates to a ReAct loop with MCP tools from Ports.
    """

    def __init__(
        self,
        # Ports (agentic MCP tool exposure + failure reporting)
        vcs: VcsPort,
        tracker: TrackerPort,
        research: DocsPort,
        brain: BrainPort,
        # Skills (deterministic pipeline)
        idempotency_check: IdempotencyCheckSkill,
        fetch_context: FetchScaffoldContextSkill,
        generate_plan: GenerateScaffoldPlanSkill,
        apply_delivery: ApplyScaffoldDeliverySkill,
        report_success: ReportSuccessSkill,
        # Agentic infrastructure
        loop_runner: AgenticLoopRunner,
        # Config
        priority_models: list[str],
        execution_mode: AgentExecutionMode = AgentExecutionMode.DETERMINISTIC,
    ):
        super().__init__(
            identity=AgentIdentity(
                name="ScaffolderAgent",
                role="Orchestrator",
                goal="Orchestrate scaffolding creation",
            ),
            brain=brain,
            priority_models=priority_models,
            execution_mode=execution_mode,
        )
        self._vcs = vcs
        self._tracker = tracker
        self._research = research
        self._idempotency_check = idempotency_check
        self._fetch_context = fetch_context
        self._generate_plan = generate_plan
        self._apply_delivery = apply_delivery
        self._report_success = report_success
        self._loop_runner = loop_runner

    # ══════════════════════════════════════════════════════════════
    #  Public entry point (used by API router)
    # ══════════════════════════════════════════════════════════════

    async def execute_flow(self, mission: Mission) -> None:
        if self._execution_mode == AgentExecutionMode.REACT_LOOP:
            await self._run_agentic_loop(mission)
        else:
            await self._run_deterministic(mission)

    # ══════════════════════════════════════════════════════════════
    #  Mode A: Deterministic Skill Pipeline
    # ══════════════════════════════════════════════════════════════

    async def _run_deterministic(self, mission: Mission) -> None:
        logger.info("[Scaffolder] Starting deterministic flow for %s", mission.key)

        config = mission.description.config
        service_name = config.get("parameters", {}).get("service_name", "")
        gitlab_project_id = config.get("target", {}).get("gitlab_project_id", "") or config.get(
            "target", {}
        ).get("gitlab_project_path", "")
        target_branch = config.get("target", {}).get("default_branch", "main")
        branch_name = ApplyScaffoldDeliverySkill.build_branch_name(mission.key, service_name)

        try:
            should_abort = await self._idempotency_check.execute(
                IdempotencyCheckInput(mission_key=mission.key, branch_name=branch_name),
            )
            if should_abort:
                return

            arch_context = await self._fetch_context.execute(service_name or mission.key)

            scaffold_plan = await self._generate_plan.execute(
                GenerateScaffoldPlanInput(
                    mission=mission,
                    arch_context=arch_context,
                    priority_models=self._priority_models,
                ),
            )

            mr_url = await self._apply_delivery.execute(
                ApplyScaffoldDeliveryInput(
                    mission_key=mission.key,
                    mission_summary=mission.summary,
                    branch_name=branch_name,
                    target_branch=target_branch,
                    scaffold_plan=scaffold_plan,
                ),
            )

            await self._report_success.execute(
                ReportSuccessInput(
                    mission_key=mission.key,
                    gitlab_project_id=gitlab_project_id,
                    branch_name=branch_name,
                    mr_url=mr_url,
                    commit_hash="",
                    files_count=len(scaffold_plan.files),
                ),
            )

            logger.info("[Scaffolder] %s completed — MR: %s", mission.key, mr_url)

        except Exception as e:
            logger.error("[Scaffolder] Critical error for %s: %s", mission.key, e, exc_info=True)
            await self._report_failure(mission.key, e)
            raise

    # ══════════════════════════════════════════════════════════════
    #  Mode B: Agentic ReAct Loop
    # ══════════════════════════════════════════════════════════════

    async def _run_agentic_loop(self, mission: Mission) -> str:
        logger.info("[Scaffolder] Starting agentic loop for %s", mission.key)

        vcs_tools = await self._vcs.get_mcp_tools()
        tracker_tools = await self._tracker.get_mcp_tools()
        docs_tools = await self._research.get_mcp_tools()
        all_tools = vcs_tools + tracker_tools + docs_tools

        async def _tool_executor(tool_name: str, arguments: dict[str, Any]) -> str:
            if tool_name.startswith("vcs_"):
                return str(await self._vcs.execute_tool(tool_name, arguments))
            if tool_name.startswith("tracker_"):
                return str(await self._tracker.execute_tool(tool_name, arguments))
            if tool_name.startswith("docs_"):
                return str(await self._research.execute_tool(tool_name, arguments))
            return f"Error: unknown tool prefix for '{tool_name}'"

        system_prompt = (
            "You are a scaffolding agent for BrahMAS.\n"
            "Your goal: create the project scaffolding, commit it to a branch, "
            "open a Merge Request, and report status to Jira.\n"
            "RULES:\n"
            "- Check if the branch already exists BEFORE creating it.\n"
            "- If the branch exists, report to Jira and STOP.\n"
            "- Never leak secrets or tokens in generated files.\n"
        )

        return await self._loop_runner.run_loop(
            mission=mission,
            system_prompt=system_prompt,
            available_tools=all_tools,
            tool_executor=_tool_executor,
            priority_models=self._priority_models,
        )

    # ══════════════════════════════════════════════════════════════
    #  Error reporting
    # ══════════════════════════════════════════════════════════════

    async def _report_failure(self, mission_key: str, error: Exception) -> None:
        try:
            await self._tracker.add_comment(mission_key, f"Fallo en Scaffolding: {error}")
        except Exception as report_err:
            logger.error("[Scaffolder] Failed to report error to Jira: %s", report_err)
