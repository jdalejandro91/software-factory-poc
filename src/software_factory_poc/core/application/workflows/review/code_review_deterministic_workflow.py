"""Deterministic code review pipeline — extracted from CodeReviewerAgent."""

import re

import structlog
from structlog.contextvars import bind_contextvars

from software_factory_poc.core.application.exceptions import (
    WorkflowExecutionError,
    WorkflowHaltedException,
)
from software_factory_poc.core.application.skills.review.analyze_code_review_skill import (
    AnalyzeCodeReviewInput,
    AnalyzeCodeReviewSkill,
)
from software_factory_poc.core.application.tools import DocsTool, TrackerTool, VcsTool
from software_factory_poc.core.application.tools.common.exceptions import ProviderError
from software_factory_poc.core.application.workflows.base_workflow import BaseWorkflow
from software_factory_poc.core.domain.delivery import FileChangesDTO
from software_factory_poc.core.domain.mission import Mission
from software_factory_poc.core.domain.quality import CodeReviewReport
from software_factory_poc.infrastructure.observability.tracing_setup import trace_operation

logger = structlog.get_logger()


class CodeReviewDeterministicWorkflow(BaseWorkflow):
    """Deterministic review pipeline: Validate -> Fetch -> Analyze -> Publish -> Report."""

    def __init__(
        self,
        vcs: VcsTool,
        tracker: TrackerTool,
        docs: DocsTool,
        analyze: AnalyzeCodeReviewSkill,
        priority_models: list[str],
    ) -> None:
        self._vcs = vcs
        self._tracker = tracker
        self._docs = docs
        self._analyze = analyze
        self._priority_models = priority_models

    @trace_operation("workflow.code_review")
    async def execute(self, mission: Mission) -> None:
        """Orchestrate the full code review pipeline."""
        bind_contextvars(mission_id=mission.id, event_type="workflow.code_review")
        logger.info("Code review workflow started", mission_key=mission.key)
        try:
            parsed = self._step_1_validate_metadata(mission)
            await self._step_2_report_start(mission)
            await self._step_3_validate_mr(mission, parsed)
            repo_tree, file_changes = await self._step_4_fetch_tree_and_diffs(parsed)
            context = await self._step_5_fetch_context(mission.summary)
            diffs_text = self._file_changes_to_diff_text(file_changes)
            report = await self._step_6_analyze(mission, diffs_text, context, parsed, repo_tree)
            await self._step_7_publish_and_transition(mission, parsed, report)
            logger.info("Code review workflow completed", mission_key=mission.key)
        except WorkflowHaltedException:
            logger.info("Code review workflow halted gracefully", mission_key=mission.key)
        except WorkflowExecutionError as wfe:
            await self._handle_error(mission, wfe)
            raise
        except Exception as exc:
            await self._handle_error(mission, exc)
            raise WorkflowExecutionError(str(exc), context={"mission_key": mission.key}) from exc

    # ── Step Methods (max 14 lines each) ─────────────────────────────

    def _step_1_validate_metadata(self, mission: Mission) -> dict[str, str]:
        """Extract and validate code_review_params YAML from the mission."""
        logger.info("Step 1: Validating code review metadata", mission_key=mission.key)
        cr_params = mission.description.config.get("code_review_params", {})
        mr_url = cr_params.get("review_request_url", "")
        project_id = cr_params.get("gitlab_project_id", "")
        branch = cr_params.get("source_branch_name", "")
        if not mr_url or not project_id:
            raise WorkflowExecutionError(
                "Missing code_review_params in mission description.",
                context={"mission_key": mission.key, "step": "validate_metadata"},
            )
        mr_iid = self._extract_mr_iid(mr_url)
        logger.info("Metadata validated", mr_iid=mr_iid, branch=branch, project_id=project_id)
        return {
            "mr_url": mr_url,
            "project_id": project_id,
            "branch": branch,
            "mr_iid": mr_iid,
        }

    async def _step_2_report_start(self, mission: Mission) -> None:
        """Announce deterministic review start."""
        logger.info("Step 2: Reporting start to tracker", mission_key=mission.key)
        await self._tracker.add_comment(
            mission.key, "Iniciando analisis de codigo (BrahMAS Code Review)..."
        )

    async def _step_3_validate_mr(self, mission: Mission, parsed: dict[str, str]) -> None:
        """Guardrail: validate both branch and MR existence before fetching diffs."""
        logger.info("Step 3: Validating branch and MR existence", mr_iid=parsed["mr_iid"])
        await self._validate_branch(parsed["branch"], parsed["mr_url"])
        mr_exists = await self._vcs.validate_merge_request_existence(parsed["mr_iid"])
        if not mr_exists:
            msg = f"El MR {parsed['mr_url']} no existe o esta cerrado."
            logger.warning("MR does not exist or is closed", mr_url=parsed["mr_url"])
            await self._tracker.add_comment(mission.key, msg)
            raise WorkflowHaltedException(msg, context={"mr_iid": parsed["mr_iid"]})
        logger.info("Branch and MR validated successfully")

    async def _step_4_fetch_tree_and_diffs(
        self, parsed: dict[str, str]
    ) -> tuple[str, list[FileChangesDTO]]:
        """Fetch lightweight directory tree and structured MR diff."""
        branch, project_id, mr_iid = parsed["branch"], parsed["project_id"], parsed["mr_iid"]
        logger.info("Step 4: Fetching repository tree and diffs", branch=branch, mr_iid=mr_iid)
        repo_tree = await self._vcs.get_repository_tree(project_id, branch)
        file_changes = await self._vcs.get_updated_code_diff(mr_iid)
        logger.info(
            "Tree and diffs fetched", tree_length=len(repo_tree), file_changes=len(file_changes)
        )
        return repo_tree, file_changes

    async def _step_5_fetch_context(self, service_name: str) -> str:
        """Retrieve architectural conventions from Confluence via Docs tool."""
        logger.info("Step 5: Fetching architecture context", service_name=service_name)
        context = await self._docs.get_architecture_context(page_id=service_name)
        logger.info("Architecture context fetched", context_length=len(context))
        return context

    async def _step_6_analyze(
        self,
        mission: Mission,
        diffs: str,
        context: str,
        parsed: dict[str, str],
        repo_tree: str = "",
    ) -> CodeReviewReport:
        """Delegate LLM analysis to the AnalyzeCodeReviewSkill."""
        logger.info("Step 6: Analyzing code via LLM", mission_key=mission.key)
        report = await self._analyze.execute(
            AnalyzeCodeReviewInput(
                mission=mission,
                mr_diff=diffs,
                conventions=context,
                priority_models=self._priority_models,
                repository_tree=repo_tree,
                code_review_params=parsed,
            ),
        )
        logger.info(
            "Code analysis completed",
            is_approved=report.is_approved,
            issues_count=len(report.comments),
        )
        return report

    async def _step_7_publish_and_transition(
        self, mission: Mission, parsed: dict[str, str], report: CodeReviewReport
    ) -> None:
        """Publish review to VCS (tolerant), post summary to tracker, transition status."""
        logger.info("Step 7: Publishing review and transitioning status")
        await self._safe_publish_review(mission, parsed["mr_iid"], report)
        await self._post_success_comment(mission, parsed["mr_url"], report)
        status = "Done" if report.is_approved else "Changes Requested"
        await self._tracker.update_status(mission.key, status)

    # ── Private Helpers (max 14 lines each) ──────────────────────────

    async def _safe_publish_review(
        self, mission: Mission, mr_iid: str, report: CodeReviewReport
    ) -> None:
        """Attempt to publish review to VCS; degrade gracefully on ProviderError."""
        try:
            await self._vcs.publish_review(mr_iid, report)
        except ProviderError as exc:
            logger.warning(
                "VCS publish failed (non-fatal)",
                mission_key=mission.key,
                error_type="ProviderError",
                error_details=exc.message,
            )
            await self._tracker.add_comment(
                mission.key,
                f"Advertencia: No se pudo publicar el review en GitLab ({exc.message}). "
                "El analisis se completo correctamente.",
            )

    async def _validate_branch(self, branch: str, mr_url: str) -> None:
        """Fail fast if the source branch does not exist."""
        if not branch:
            raise WorkflowExecutionError(
                f"Source branch is empty for MR: {mr_url}",
                context={"mr_url": mr_url, "step": "validate_branch"},
            )
        exists = await self._vcs.validate_branch_existence(branch)
        if not exists:
            raise WorkflowExecutionError(
                f"Branch '{branch}' not found in remote repository.",
                context={"branch": branch, "step": "validate_branch"},
            )

    async def _post_success_comment(
        self, mission: Mission, mr_url: str, report: CodeReviewReport
    ) -> None:
        """Post a summary comment to Jira with the review verdict."""
        verdict = "APPROVED" if report.is_approved else "CHANGES REQUESTED"
        comment = (
            f"Code Review completado: **{verdict}**\n"
            f"- MR: {mr_url}\n"
            f"- Issues encontrados: {len(report.comments)}\n"
            f"- Resumen: {report.summary}"
        )
        await self._tracker.add_comment(mission.key, comment)

    @staticmethod
    def _file_changes_to_diff_text(file_changes: list[FileChangesDTO]) -> str:
        """Reconstruct unified diff text from structured FileChangesDTO list."""
        sections: list[str] = []
        for fc in file_changes:
            header = f"--- {fc.old_path or '/dev/null'}\n+++ {fc.new_path}"
            sections.append(header + "\n" + "\n".join(fc.hunks))
        return "\n".join(sections)

    async def _handle_error(self, mission: Mission, error: Exception) -> None:
        """Log failure with Puntored schema and notify Jira."""
        if isinstance(error, ProviderError):
            msg = f"VCS provider error ({error.provider}): {error.message}"
        else:
            msg = f"Review failed: {type(error).__name__}: {error}"
        logger.error(
            "Code review workflow failed",
            mission_key=mission.key,
            processing_status="ERROR",
            error_type=type(error).__name__,
            error_details=str(error),
            error_retryable=False,
        )
        await self._tracker.add_comment(mission.key, msg)

    @staticmethod
    def _extract_mr_iid(mr_url: str) -> str:
        """Extract the MR IID from a GitLab Merge Request URL."""
        match = re.search(r"merge_requests/(\d+)", mr_url)
        if match:
            return match.group(1)
        if mr_url.strip().isdigit():
            return mr_url.strip()
        raise WorkflowExecutionError(
            f"Cannot extract MR IID from URL: '{mr_url}'",
            context={"mr_url": mr_url, "step": "extract_mr_iid"},
        )
