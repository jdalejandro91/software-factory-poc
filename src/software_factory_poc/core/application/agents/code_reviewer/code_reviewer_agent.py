import logging
import re
from collections.abc import Mapping
from typing import Any, cast

from software_factory_poc.core.application.agents.common.agent_config import (
    CodeReviewerAgentConfig,
)
from software_factory_poc.core.application.agents.common.agent_execution_mode import (
    AgentExecutionMode,
)
from software_factory_poc.core.application.agents.common.base_agent import AgentIdentity, BaseAgent
from software_factory_poc.core.application.agents.loops.agentic_loop_runner import (
    AgenticLoopRunner,
)
from software_factory_poc.core.application.policies.tool_safety_policy import ToolSafetyPolicy
from software_factory_poc.core.application.skills.review.analyze_code_review_skill import (
    AnalyzeCodeReviewInput,
    AnalyzeCodeReviewSkill,
)
from software_factory_poc.core.application.skills.skill import BaseSkill
from software_factory_poc.core.application.tools import BrainTool, DocsTool, TrackerTool, VcsTool
from software_factory_poc.core.application.tools.common.exceptions import ProviderError
from software_factory_poc.core.domain.delivery import FileContent
from software_factory_poc.core.domain.mission import Mission
from software_factory_poc.core.domain.quality import CodeReviewReport
from software_factory_poc.core.domain.shared.base_tool import BaseTool
from software_factory_poc.core.domain.shared.skill_type import SkillType
from software_factory_poc.core.domain.shared.tool_type import ToolType

logger = logging.getLogger(__name__)


class CodeReviewerAgent(BaseAgent):
    """BrahMAS Code Reviewer Agent — Dual-Flow (Deterministic + Agentic)."""

    def __init__(
        self,
        config: CodeReviewerAgentConfig,
        tools: Mapping[ToolType, BaseTool],
        skills: Mapping[SkillType, BaseSkill[Any, Any]],
    ):
        super().__init__(
            identity=AgentIdentity(
                name="CodeReviewerAgent",
                role="Reviewer",
                goal="Perform automated code reviews",
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
        self._analyze = cast(AnalyzeCodeReviewSkill, skills[SkillType.ANALYZE_CODE_REVIEW])

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
            parsed = await self._step_1_parse_mission(mission)
            await self._step_2_report_start(mission)
            await self._step_3_validate_existence(parsed["branch"], parsed["mr_url"])
            branch_code = await self._step_4_fetch_branch_code(
                parsed["project_id"], parsed["branch"]
            )
            diffs = await self._step_5_fetch_mr_diffs(parsed["mr_iid"])
            context = await self._step_6_fetch_docs_context(mission.summary)
            report = await self._step_7_analyze_code(mission, branch_code, diffs, context)
            await self._step_8_publish_review(parsed["mr_iid"], report)
            await self._step_9_report_success(mission, parsed["mr_url"], report)
            await self._step_10_transition_status(mission, report)
        except Exception as exc:
            await self._step_11_handle_error(mission, exc)
            raise

    # ── Step Methods (max 14 lines each) ─────────────────────────────

    async def _step_1_parse_mission(self, mission: Mission) -> dict[str, str]:
        """Extract and validate code_review_params YAML from the mission."""
        cr_params = mission.description.config.get("code_review_params", {})
        mr_url = cr_params.get("review_request_url", "")
        project_id = cr_params.get("gitlab_project_id", "")
        branch = cr_params.get("source_branch_name", "")
        if not mr_url or not project_id:
            raise ValueError("Missing code_review_params in mission description.")
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

    async def _step_3_validate_existence(self, branch: str, mr_url: str) -> None:
        """Fail fast if the source branch does not exist."""
        if not branch:
            raise ValueError(f"Source branch is empty for MR: {mr_url}")
        exists = await self._vcs.validate_branch_existence(branch)
        if not exists:
            raise ValueError(f"Branch '{branch}' not found in remote repository.")

    async def _step_4_fetch_branch_code(self, project: str, branch: str) -> list[FileContent]:
        """Retrieve source branch file listing via VCS tool."""
        logger.info("[Reviewer] Fetching branch code: %s", branch)
        return await self._vcs.get_original_branch_code(project, branch)

    async def _step_5_fetch_mr_diffs(self, mr_iid: str) -> str:
        """Retrieve the unified MR diff via VCS tool."""
        logger.info("[Reviewer] Fetching MR diff for IID %s", mr_iid)
        return await self._vcs.get_updated_code_diff(mr_iid)

    async def _step_6_fetch_docs_context(self, service_name: str) -> str:
        """Retrieve architectural conventions from Confluence via Docs tool."""
        logger.info("[Reviewer] Fetching docs context for '%s'", service_name)
        return await self._docs.get_architecture_context(service_name)

    async def _step_7_analyze_code(
        self, mission: Mission, branch_code: list[FileContent], diffs: str, context: str
    ) -> CodeReviewReport:
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

    async def _step_8_publish_review(self, mr_iid: str, report: CodeReviewReport) -> None:
        """Publish inline review comments to the Merge Request via VCS tool."""
        logger.info("[Reviewer] Publishing review to MR %s", mr_iid)
        await self._vcs.publish_review(mr_iid, report)

    async def _step_9_report_success(
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

    async def _step_10_transition_status(self, mission: Mission, report: CodeReviewReport) -> None:
        """Transition Jira ticket based on review outcome."""
        status = "Done" if report.is_approved else "Changes Requested"
        await self._tracker.update_status(mission.key, status)

    async def _step_11_handle_error(self, mission: Mission, error: Exception) -> None:
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
        raise ValueError(f"Cannot extract MR IID from URL: '{mr_url}'")

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
