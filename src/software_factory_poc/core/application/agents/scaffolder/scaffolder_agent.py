import logging
from typing import Any

from software_factory_poc.core.application.agents.common.agent_execution_mode import (
    AgentExecutionMode,
)
from software_factory_poc.core.application.agents.common.agent_structures import AgentPorts
from software_factory_poc.core.application.agents.common.base_agent import AgentIdentity, BaseAgent
from software_factory_poc.core.application.agents.loops.agentic_loop_runner import (
    AgenticLoopRunner,
)
from software_factory_poc.core.application.agents.scaffolder.config.scaffolder_agent_di_config import (
    ScaffolderAgentConfig,
)
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
from software_factory_poc.core.domain.mission import Mission

logger = logging.getLogger(__name__)


class ScaffolderAgent(BaseAgent):
    """BrahMAS Scaffolder Agent — Dual-Flow (Deterministic + Agentic)."""

    def __init__(
        self,
        config: ScaffolderAgentConfig,
        ports: AgentPorts,
        idempotency_check: IdempotencyCheckSkill,
        fetch_context: FetchScaffoldContextSkill,
        generate_plan: GenerateScaffoldPlanSkill,
        apply_delivery: ApplyScaffoldDeliverySkill,
        report_success: ReportSuccessSkill,
        loop_runner: AgenticLoopRunner,
    ):
        super().__init__(
            identity=AgentIdentity(
                name="ScaffolderAgent",
                role="Orchestrator",
                goal="Orchestrate scaffolding creation",
            ),
            brain=ports.brain,
            priority_models=config.priority_models,
            execution_mode=config.execution_mode,
        )
        self._config = config
        self._ports = ports
        self._idempotency_check = idempotency_check
        self._fetch_context = fetch_context
        self._generate_plan = generate_plan
        self._apply_delivery = apply_delivery
        self._report_success = report_success
        self._loop_runner = loop_runner

    async def run(self, mission: Mission) -> None:
        """Public entry point — dispatches to deterministic or agentic mode."""
        if self._execution_mode == AgentExecutionMode.REACT_LOOP:
            await self._run_agentic_loop(mission)
        else:
            await self._run_deterministic(mission)

    async def _run_deterministic(self, mission: Mission) -> Any:
        logger.info("[Scaffolder] Starting deterministic flow for %s", mission.key)

        cfg = mission.description.config
        service_name = cfg.get("parameters", {}).get("service_name", "")
        project_id = cfg.get("target", {}).get("gitlab_project_id", "") or cfg.get(
            "target", {}
        ).get("gitlab_project_path", "")
        target_branch = cfg.get("target", {}).get("default_branch", "main")
        branch_name = ApplyScaffoldDeliverySkill.build_branch_name(mission.key, service_name)

        if await self._idempotency_check.execute(
            IdempotencyCheckInput(mission_key=mission.key, branch_name=branch_name),
        ):
            return

        arch_context = await self._fetch_context.execute(service_name or mission.key)

        plan = await self._generate_plan.execute(
            GenerateScaffoldPlanInput(
                mission=mission, arch_context=arch_context, priority_models=self._priority_models
            ),
        )

        mr_url = await self._apply_delivery.execute(
            ApplyScaffoldDeliveryInput(
                mission_key=mission.key,
                mission_summary=mission.summary,
                branch_name=branch_name,
                target_branch=target_branch,
                scaffold_plan=plan,
            ),
        )

        await self._report_success.execute(
            ReportSuccessInput(
                mission_key=mission.key,
                gitlab_project_id=project_id,
                branch_name=branch_name,
                mr_url=mr_url,
                commit_hash="",
                files_count=len(plan.files),
            ),
        )

        logger.info("[Scaffolder] %s completed — MR: %s", mission.key, mr_url)

    async def _run_agentic_loop(self, mission: Mission) -> None:
        logger.info("[Scaffolder] Starting agentic loop for %s", mission.key)

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
            available_tools=all_tools,
            tool_executor=_tool_executor,
            priority_models=self._priority_models,
            max_iterations=self._config.max_iterations,
        )
