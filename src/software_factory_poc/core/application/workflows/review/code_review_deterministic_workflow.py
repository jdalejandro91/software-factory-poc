"""Deterministic code review pipeline — extracted from CodeReviewerAgent."""

import logging
import re

from software_factory_poc.core.application.exceptions import WorkflowExecutionError
from software_factory_poc.core.application.skills.review.analyze_code_review_skill import (
    AnalyzeCodeReviewInput,
    AnalyzeCodeReviewSkill,
)
from software_factory_poc.core.application.tools import DocsTool, TrackerTool, VcsTool
from software_factory_poc.core.application.tools.common.exceptions import ProviderError
from software_factory_poc.core.application.workflows.base_workflow import BaseWorkflow
from software_factory_poc.core.domain.delivery import FileContent
from software_factory_poc.core.domain.mission import Mission
from software_factory_poc.core.domain.quality import CodeReviewReport

logger = logging.getLogger(__name__)


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

    async def execute(self, mission: Mission) -> None:
        """Orchestrate the full code review pipeline."""
        try:
            parsed = self._step_1_validate_metadata(mission)
            await self._step_2_report_start(mission)
            _, diffs = await self._step_3_fetch_code_and_diffs(parsed)
            context = await self._step_4_fetch_context(mission.summary)
            report = await self._step_5_analyze(mission, diffs, context)
            await self._step_6_publish_and_transition(mission, parsed, report)
        except WorkflowExecutionError as wfe:
            await self._handle_error(mission, wfe)
            raise
        except Exception as exc:
            await self._handle_error(mission, exc)
            raise WorkflowExecutionError(str(exc), context={"mission_key": mission.key}) from exc

    # ── Step Methods (max 14 lines each) ─────────────────────────────

    def _step_1_validate_metadata(self, mission: Mission) -> dict[str, str]:
        """Extract and validate code_review_params YAML from the mission."""
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
        return {
            "mr_url": mr_url,
            "project_id": project_id,
            "branch": branch,
            "mr_iid": mr_iid,
        }

    async def _step_2_report_start(self, mission: Mission) -> None:
        """Announce deterministic review start."""
        logger.info("[Reviewer] Starting deterministic flow for %s", mission.key)
        await self._tracker.add_comment(
            mission.key, "Iniciando analisis de codigo (BrahMAS Code Review)..."
        )

    async def _step_3_fetch_code_and_diffs(
        self, parsed: dict[str, str]
    ) -> tuple[list[FileContent], str]:
        """Validate branch existence, fetch source code and MR diff."""
        branch, project_id, mr_iid = parsed["branch"], parsed["project_id"], parsed["mr_iid"]
        await self._validate_branch(branch, parsed["mr_url"])
        branch_code = await self._vcs.get_original_branch_code(project_id, branch)
        diffs = await self._vcs.get_updated_code_diff(mr_iid)
        return branch_code, diffs

    async def _step_4_fetch_context(self, service_name: str) -> str:
        """Retrieve architectural conventions from Confluence via Docs tool."""
        logger.info("[Reviewer] Fetching docs context for '%s'", service_name)
        return await self._docs.get_architecture_context(service_name)

    async def _step_5_analyze(self, mission: Mission, diffs: str, context: str) -> CodeReviewReport:
        """Delegate LLM analysis to the AnalyzeCodeReviewSkill."""
        return await self._analyze.execute(
            AnalyzeCodeReviewInput(
                mission_summary=mission.summary,
                mission_description=mission.description.raw_content,
                mr_diff=diffs,
                conventions=context,
                priority_models=self._priority_models,
            ),
        )

    async def _step_6_publish_and_transition(
        self, mission: Mission, parsed: dict[str, str], report: CodeReviewReport
    ) -> None:
        """Publish review to VCS, post summary to tracker, transition status."""
        await self._vcs.publish_review(parsed["mr_iid"], report)
        await self._post_success_comment(mission, parsed["mr_url"], report)
        status = "Done" if report.is_approved else "Changes Requested"
        await self._tracker.update_status(mission.key, status)

    # ── Private Helpers (max 14 lines each) ──────────────────────────

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
        logger.info("[Reviewer] %s completed — %s", mission.key, verdict)

    async def _handle_error(self, mission: Mission, error: Exception) -> None:
        """Log failure and notify Jira. Handles ProviderError for unsupported VCS."""
        if isinstance(error, ProviderError):
            msg = f"VCS provider error ({error.provider}): {error.message}"
        else:
            msg = f"Review failed: {type(error).__name__}: {error}"
        logger.exception("[Reviewer] %s failed: %s", mission.key, error)
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
