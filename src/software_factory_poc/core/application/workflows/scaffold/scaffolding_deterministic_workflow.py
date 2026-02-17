"""Deterministic scaffolding pipeline — extracted from ScaffolderAgent."""

import logging
import re

from software_factory_poc.core.application.exceptions import (
    WorkflowExecutionError,
    WorkflowHaltedException,
)
from software_factory_poc.core.application.skills.scaffold.contracts.scaffolder_contracts import (
    ScaffoldingResponseSchema,
)
from software_factory_poc.core.application.skills.scaffold.generate_scaffold_plan_skill import (
    GenerateScaffoldPlanInput,
    GenerateScaffoldPlanSkill,
)
from software_factory_poc.core.application.tools import DocsTool, TrackerTool, VcsTool
from software_factory_poc.core.application.workflows.base_workflow import BaseWorkflow
from software_factory_poc.core.domain.delivery import BranchName, CommitIntent, FileContent
from software_factory_poc.core.domain.mission import Mission

logger = logging.getLogger(__name__)


class ScaffoldingDeterministicWorkflow(BaseWorkflow):
    """Deterministic scaffolding pipeline: Parse -> Idempotency -> Context -> Plan -> Deliver -> Report."""

    def __init__(
        self,
        vcs: VcsTool,
        tracker: TrackerTool,
        docs: DocsTool,
        generate_plan: GenerateScaffoldPlanSkill,
        priority_models: list[str],
    ) -> None:
        self._vcs = vcs
        self._tracker = tracker
        self._docs = docs
        self._generate_plan = generate_plan
        self._priority_models = priority_models

    async def execute(self, mission: Mission) -> None:
        """Orchestrate the full scaffolding pipeline."""
        try:
            parsed = self._parse_mission(mission)
            await self._step_1_report_start(mission)
            await self._step_2_check_idempotency(mission, parsed["branch_name"])
            context = await self._step_3_fetch_context(parsed["service_name"] or mission.key)
            plan = await self._step_4_generate_plan(mission, context)
            commit_hash, mr_url = await self._step_5_create_and_commit(mission, parsed, plan)
            await self._step_6_report_success(mission, parsed, commit_hash, mr_url, len(plan.files))
        except WorkflowHaltedException:
            logger.info("[Scaffold] Workflow halted gracefully for %s", mission.key)
        except WorkflowExecutionError as wfe:
            await self._handle_error(mission, wfe)
            raise
        except Exception as exc:
            await self._handle_error(mission, exc)
            raise WorkflowExecutionError(str(exc), context={"mission_key": mission.key}) from exc

    # ── Step Methods (max 14 lines each) ─────────────────────────────

    def _parse_mission(self, mission: Mission) -> dict[str, str]:
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

    async def _step_1_report_start(self, mission: Mission) -> None:
        """Announce deterministic flow start."""
        logger.info("[Scaffold] Starting deterministic flow for %s", mission.key)
        await self._tracker.add_comment(
            mission.key, "Iniciando tarea de Scaffolding (BrahMAS Engine)..."
        )

    async def _step_2_check_idempotency(self, mission: Mission, branch_name: str) -> None:
        """Fail with WorkflowHaltedException if branch already exists."""
        branch_exists = await self._vcs.validate_branch_existence(branch_name)
        if branch_exists:
            msg = f"La rama '{branch_name}' ya existe. Deteniendo ejecucion."
            logger.warning("[Scaffold] %s", msg)
            await self._tracker.add_comment(mission.key, msg)
            await self._tracker.update_status(mission.key, "In Review")
            raise WorkflowHaltedException(msg, context={"branch": branch_name})

    async def _step_3_fetch_context(self, service_name: str) -> str:
        """Retrieve architectural context from Confluence via DocsTool."""
        logger.info("[Scaffold] Fetching architecture context for '%s'", service_name)
        return await self._docs.get_architecture_context(service_name)

    async def _step_4_generate_plan(
        self, mission: Mission, arch_context: str
    ) -> ScaffoldingResponseSchema:
        """Delegate prompt building + LLM call to the GenerateScaffoldPlanSkill."""
        plan = await self._generate_plan.execute(
            GenerateScaffoldPlanInput(
                mission=mission, arch_context=arch_context, priority_models=self._priority_models
            ),
        )
        if not plan.files:
            raise WorkflowExecutionError(
                "LLM returned 0 files — cannot proceed with scaffolding.",
                context={"mission_key": mission.key, "step": "generate_plan"},
            )
        return plan

    async def _step_5_create_and_commit(
        self,
        mission: Mission,
        parsed: dict[str, str],
        plan: ScaffoldingResponseSchema,
    ) -> tuple[str, str]:
        """Create branch, commit files, open MR. Returns (commit_hash, mr_url)."""
        branch, target = parsed["branch_name"], parsed["target_branch"]
        await self._vcs.create_branch(branch, ref=target)
        commit_hash = await self._vcs.commit_changes(self._build_commit_intent(branch, plan))
        mr_url = await self._vcs.create_merge_request(
            source_branch=branch,
            target_branch=target,
            title=f"feat: Scaffolding {mission.key}",
            description=f"Auto-generated by BrahMAS.\n\n{mission.summary}",
        )
        return commit_hash, mr_url

    async def _step_6_report_success(
        self,
        mission: Mission,
        parsed: dict[str, str],
        commit_hash: str,
        mr_url: str,
        files_count: int,
    ) -> None:
        """Update task description, post success comment, transition status."""
        await self._update_task_description(
            mission, mr_url, parsed["project_id"], parsed["branch_name"]
        )
        await self._post_success_comment(
            mission, mr_url, parsed["branch_name"], commit_hash, files_count
        )
        await self._tracker.update_status(mission.key, "In Review")

    # ── Private Helpers (max 14 lines each) ──────────────────────────

    async def _update_task_description(
        self, mission: Mission, mr_url: str, project_id: str, branch_name: str
    ) -> None:
        yaml_block = (
            f"\n\n---\ncode_review_params:\n"
            f'  gitlab_project_id: "{project_id}"\n'
            f'  source_branch_name: "{branch_name}"\n'
            f'  review_request_url: "{mr_url}"\n'
        )
        await self._tracker.update_task_description(
            mission.key, mission.description.raw_content + yaml_block
        )

    async def _post_success_comment(
        self, mission: Mission, mr_url: str, branch: str, commit_hash: str, files_count: int
    ) -> None:
        comment = (
            f"Scaffolding completado exitosamente.\n"
            f"- Merge Request: {mr_url}\n- Rama: {branch}\n"
            f"- Commit: {commit_hash}\n- Archivos generados: {files_count}"
        )
        await self._tracker.add_comment(mission.key, comment)
        logger.info("[Scaffold] %s completed — MR: %s", mission.key, mr_url)

    async def _handle_error(self, mission: Mission, error: Exception) -> None:
        logger.exception("[Scaffold] %s failed: %s", mission.key, error)
        await self._tracker.add_comment(
            mission.key, f"Scaffolding failed: {type(error).__name__}: {error}"
        )

    @staticmethod
    def _build_branch_name(mission_key: str, service_name: str = "") -> str:
        safe_key = re.sub(r"[^a-z0-9\-]", "", mission_key.lower())
        if service_name:
            safe_service = re.sub(r"[^a-z0-9\-]", "-", service_name.lower().strip())
            return f"feature/{safe_key}-{safe_service}"
        return f"feature/{safe_key}-scaffolder"

    @staticmethod
    def _build_commit_intent(branch: str, plan: ScaffoldingResponseSchema) -> CommitIntent:
        return CommitIntent(
            branch=BranchName(value=branch),
            message=plan.commit_message,
            files=[
                FileContent(path=f.path, content=f.content, is_new=f.is_new) for f in plan.files
            ],
        )
