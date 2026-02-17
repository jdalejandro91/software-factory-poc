import logging
import re
from collections.abc import Mapping
from typing import Any, cast

from software_factory_poc.core.application.agents.common.agent_config import ScaffolderAgentConfig
from software_factory_poc.core.application.agents.common.agent_execution_mode import (
    AgentExecutionMode,
)
from software_factory_poc.core.application.agents.common.base_agent import AgentIdentity, BaseAgent
from software_factory_poc.core.application.agents.loops.agentic_loop_runner import (
    AgenticLoopRunner,
)
from software_factory_poc.core.application.agents.scaffolder.contracts.scaffolder_contracts import (
    ScaffoldingResponseSchema,
)
from software_factory_poc.core.application.policies.tool_safety_policy import ToolSafetyPolicy
from software_factory_poc.core.application.skills.scaffold.generate_scaffold_plan_skill import (
    GenerateScaffoldPlanInput,
    GenerateScaffoldPlanSkill,
)
from software_factory_poc.core.application.skills.skill import BaseSkill
from software_factory_poc.core.application.tools import BrainTool, DocsTool, TrackerTool, VcsTool
from software_factory_poc.core.domain.delivery import BranchName, CommitIntent, FileContent
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
        tools: Mapping[ToolType, BaseTool],
        skills: Mapping[SkillType, BaseSkill[Any, Any]],
    ):
        super().__init__(
            identity=AgentIdentity(
                name="ScaffolderAgent",
                role="Orchestrator",
                goal="Orchestrate scaffolding creation",
            ),
            config=config,
            tools=tools,
            skills=skills,
        )
        # Extract typed tools
        self._vcs = cast(VcsTool, tools[ToolType.VCS])
        self._tracker = cast(TrackerTool, tools[ToolType.TRACKER])
        self._docs = cast(DocsTool, tools[ToolType.DOCS])
        self._brain = cast(BrainTool, tools[ToolType.BRAIN])

        # Extract typed skills (only brain-heavy skills remain)
        self._generate_plan = cast(
            GenerateScaffoldPlanSkill, skills[SkillType.GENERATE_SCAFFOLD_PLAN]
        )

        # Build loop runner from injected brain
        self._loop_runner = AgenticLoopRunner(brain=self._brain, policy=ToolSafetyPolicy())

    async def run(self, mission: Mission) -> None:
        """Public entry point — dispatches to deterministic or agentic mode."""
        if self._execution_mode == AgentExecutionMode.REACT_LOOP:
            await self._run_agentic_loop(mission)
        else:
            await self._run_deterministic(mission)

    async def _run_deterministic(self, mission: Mission) -> None:
        try:
            await self._step_2_report_start(mission)
            parsed = await self._step_1_parse_mission(mission)
            if await self._step_3_check_idempotency(mission, parsed["branch_name"]):
                return
            context = await self._step_4_fetch_context(parsed["service_name"] or mission.key)
            plan = await self._step_5_and_6_generate_plan(mission, context)
            self._step_7_validate_plan(plan)
            await self._step_8_create_branch(
                parsed["project_id"], parsed["branch_name"], parsed["target_branch"]
            )
            commit_hash = await self._step_9_commit_files(parsed["branch_name"], plan)
            mr_url = await self._step_10_create_mr(
                parsed["project_id"], parsed["branch_name"], parsed["target_branch"], mission
            )
            await self._step_11_update_task_description(
                mission, mr_url, parsed["project_id"], parsed["branch_name"]
            )
            await self._step_12_report_success(
                mission, mr_url, parsed["branch_name"], commit_hash, len(plan.files)
            )
            await self._step_13_transition_status(mission)
        except Exception as exc:
            await self._step_14_handle_error(mission, exc)
            raise

    # ── Step Methods (max 14 lines each) ─────────────────────────────

    async def _step_1_parse_mission(self, mission: Mission) -> dict[str, str]:
        """Extract and validate mission configuration from YAML."""
        cfg = mission.description.config
        service_name = cfg.get("parameters", {}).get("service_name", "")
        project_id = cfg.get("target", {}).get("gitlab_project_id", "") or cfg.get(
            "target", {}
        ).get("gitlab_project_path", "")
        target_branch = cfg.get("target", {}).get("default_branch", "main")
        branch_name = self._build_branch_name(mission.key, service_name)
        return {
            "service_name": service_name,
            "project_id": project_id,
            "target_branch": target_branch,
            "branch_name": branch_name,
        }

    async def _step_2_report_start(self, mission: Mission) -> None:
        """Announce deterministic flow start."""
        logger.info("[Scaffolder] Starting deterministic flow for %s", mission.key)

    async def _step_3_check_idempotency(self, mission: Mission, branch_name: str) -> bool:
        """Notify tracker and check if branch already exists. Returns True to abort."""
        await self._tracker.add_comment(
            mission.key, "Iniciando tarea de Scaffolding (BrahMAS Engine)..."
        )
        branch_exists = await self._vcs.validate_branch_existence(branch_name)
        if branch_exists:
            msg = (
                f"La rama '{branch_name}' ya existe en el repositorio. "
                "Deteniendo ejecucion para evitar sobreescritura."
            )
            logger.warning("[Scaffolder] %s", msg)
            await self._tracker.add_comment(mission.key, msg)
            await self._tracker.update_status(mission.key, "In Review")
            return True
        return False

    async def _step_4_fetch_context(self, service_name: str) -> str:
        """Retrieve architectural context from Confluence via DocsTool."""
        logger.info("[Scaffolder] Fetching architecture context for '%s'", service_name)
        return await self._docs.get_architecture_context(service_name)

    async def _step_5_and_6_generate_plan(
        self, mission: Mission, arch_context: str
    ) -> ScaffoldingResponseSchema:
        """Delegate prompt building + LLM call to the GenerateScaffoldPlanSkill."""
        return await self._generate_plan.execute(
            GenerateScaffoldPlanInput(
                mission=mission, arch_context=arch_context, priority_models=self._priority_models
            ),
        )

    def _step_7_validate_plan(self, plan: ScaffoldingResponseSchema) -> None:
        """Fail fast if the LLM returned an empty scaffold plan."""
        if not plan.files:
            raise ValueError("LLM returned 0 files — cannot proceed with scaffolding.")

    async def _step_8_create_branch(self, project: str, branch: str, target: str) -> None:
        """Create feature branch from target via VCS tool."""
        logger.info("[Scaffolder] Creating branch '%s' from '%s'", branch, target)
        await self._vcs.create_branch(branch, ref=target)

    async def _step_9_commit_files(self, branch: str, plan: ScaffoldingResponseSchema) -> str:
        """Map LLM response to a domain CommitIntent and commit. Returns hash."""
        intent = CommitIntent(
            branch=BranchName(value=branch),
            message=plan.commit_message,
            files=[
                FileContent(path=f.path, content=f.content, is_new=f.is_new) for f in plan.files
            ],
        )
        logger.info("[Scaffolder] Committing %d files to '%s'", len(intent.files), branch)
        return await self._vcs.commit_changes(intent)

    async def _step_10_create_mr(
        self, project: str, branch: str, target: str, mission: Mission
    ) -> str:
        """Open a Merge Request and return the web URL."""
        logger.info("[Scaffolder] Creating MR: %s -> %s", branch, target)
        return await self._vcs.create_merge_request(
            source_branch=branch,
            target_branch=target,
            title=f"feat: Scaffolding {mission.key}",
            description=f"Auto-generated by BrahMAS.\n\n{mission.summary}",
        )

    async def _step_11_update_task_description(
        self, mission: Mission, mr_url: str, project_id: str, branch_name: str
    ) -> None:
        """Inject code_review_params YAML into the Jira task description."""
        yaml_block = (
            f"\n\n---\ncode_review_params:\n"
            f'  gitlab_project_id: "{project_id}"\n'
            f'  source_branch_name: "{branch_name}"\n'
            f'  review_request_url: "{mr_url}"\n'
        )
        updated = mission.description.raw_content + yaml_block
        await self._tracker.update_task_description(mission.key, updated)

    async def _step_12_report_success(
        self, mission: Mission, mr_url: str, branch: str, commit_hash: str, files_count: int
    ) -> None:
        """Post a success summary comment to Jira."""
        comment = (
            f"Scaffolding completado exitosamente.\n"
            f"- Merge Request: {mr_url}\n"
            f"- Rama: {branch}\n"
            f"- Commit: {commit_hash}\n"
            f"- Archivos generados: {files_count}"
        )
        await self._tracker.add_comment(mission.key, comment)
        logger.info("[Scaffolder] %s completed — MR: %s", mission.key, mr_url)

    async def _step_13_transition_status(self, mission: Mission) -> None:
        """Move the Jira ticket to 'In Review'."""
        await self._tracker.update_status(mission.key, "In Review")

    async def _step_14_handle_error(self, mission: Mission, error: Exception) -> None:
        """Log failure and notify Jira with the error details."""
        logger.exception("[Scaffolder] %s failed: %s", mission.key, error)
        await self._tracker.add_comment(
            mission.key, f"Scaffolding failed: {type(error).__name__}: {error}"
        )

    # ── Utilities ─────────────────────────────────────────────────────

    @staticmethod
    def _build_branch_name(mission_key: str, service_name: str = "") -> str:
        """Build a deterministic, safe branch name from mission key."""
        safe_key = re.sub(r"[^a-z0-9\-]", "", mission_key.lower())
        if service_name:
            safe_service = re.sub(r"[^a-z0-9\-]", "-", service_name.lower().strip())
            return f"feature/{safe_key}-{safe_service}"
        return f"feature/{safe_key}-scaffolder"

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
