from dataclasses import dataclass
from typing import Any, List, Tuple

from software_factory_poc.application.core.agents.base_agent import BaseAgent
from software_factory_poc.application.core.agents.code_reviewer.config.code_reviewer_agent_config import (
    CodeReviewerAgentConfig,
)
from software_factory_poc.application.core.agents.code_reviewer.tools.code_review_prompt_builder import (
    CodeReviewPromptBuilder,
)
from software_factory_poc.application.core.agents.code_reviewer.tools.review_result_parser import ReviewResultParser
from software_factory_poc.application.core.agents.common.dtos.file_changes_dto import FileChangesDTO
from software_factory_poc.application.core.agents.common.dtos.file_content_dto import FileContentDTO
from software_factory_poc.application.core.agents.reasoner.reasoner_agent import ReasonerAgent
from software_factory_poc.application.core.agents.reporter.reporter_agent import ReporterAgent
from software_factory_poc.application.core.agents.research.research_agent import ResearchAgent
from software_factory_poc.application.core.agents.vcs.vcs_agent import VcsAgent
from software_factory_poc.application.core.agents.code_reviewer.value_objects.code_review_order import (
    CodeReviewOrder,
)
from software_factory_poc.infrastructure.observability.logger_factory_service import LoggerFactoryService


@dataclass
class CodeReviewerAgent(BaseAgent):
    """
    Orchestrator Agent for Code Review Tasks.
    """

    config: CodeReviewerAgentConfig
    reporter: ReporterAgent
    vcs: VcsAgent
    researcher: ResearchAgent
    reasoner: ReasonerAgent

    def __post_init__(self):
        self.logger = LoggerFactoryService.build_logger(__name__)
        self.prompt_builder = CodeReviewPromptBuilder()
        self.parser = ReviewResultParser()
        self.logger.info("CodeReviewerAgent initialized")

    def execute_flow(self, order: CodeReviewOrder) -> None:
        self.logger.info(f"Starting code review for {order}")
        
        try:
            # 3.1 Report Start
            self.reporter.report_start(order.issue_key)
            
            # 3.2 Validate Provider
            if order.vcs_provider.upper() != "GITLAB":
                msg = f"Provider '{order.vcs_provider}' not supported yet. Only GITLAB is supported."
                self.logger.warning(msg)
                self.reporter.report_failure(order.issue_key, msg)
                return

            # 3.3 Validate MR Existence
            exists = self.vcs.validate_mr(order.project_id, order.mr_id)
            if not exists:
                msg = f"Merge Request {order.mr_id} not found in project {order.project_id}"
                self.logger.error(msg)
                self.reporter.report_failure(order.issue_key, msg)
                return

            self.logger.info(f"MR {order.mr_id} validated. Proceeding with review...")
            
            # 3.4 Fetch Artifacts and Validate Diff
            original_code, changes = self._fetch_review_artifacts(order)
            
            if not changes:
                msg = "Review skipped: No changes detected in MR."
                self.logger.info(msg)
                self.reporter.report_success(order.issue_key, msg)
                return

            # 3.5 Gather Technical Context
            query = f"Standards and guidelines for {order.summary}"
            technical_context = self.researcher.investigate(
                query=query,
                specific_page_id=order.technical_doc_id
            )
            self.logger.info(f"Research complete. Context size: {len(technical_context)} chars")

            # 3.8 Prompt Construction
            prompt = self.prompt_builder.build_prompt(
                diffs=changes,
                original_files=original_code,
                technical_context=technical_context,
                requirements=f"{order.summary}\n\n{order.description}"
            )
            self.logger.info("Prompt constructed successfully.")

            # 3.9 Reasoning (LLM)
            raw_response = self.reasoner.reason(
                prompt=prompt,
                model_id=self.config.llm_model_priority
            )
            self.logger.info(f"LLM response received. Length: {len(raw_response)} chars")

            # 3.10 Parse Result
            review_result = self.parser.parse(raw_response)
            self.logger.info(f"Review parsed successfully. Verdict: {review_result.verdict}. Comments: {len(review_result.comments)}")

            # 3.11 Submit Review
            self.vcs.submit_review(order.project_id, order.mr_id, review_result.comments)
            self.logger.info("Review comments submitted to VCS.")

            # 3.12 Report Success (Without transitioning)
            verdict_emoji = {
                "APPROVE": "✅",
                "COMMENT": "💬",
                "REQUEST_CHANGES": "🛑"
            }.get(review_result.verdict.name, "📋")

            # Format requested: "Code Review Completed. Comments posted on MR: {link}. Verdict: {verdict}."
            mr_link = order.mr_url or f"MR ID: {order.mr_id}"
            
            report_payload = {
                "type": "code_review_completion",
                "title": f"Code Review Finalizado: {verdict_emoji} {review_result.verdict.name}",
                "summary": f"Code Review Completed. Comments posted on MR: {mr_link}. Verdict: {review_result.verdict.name}",
                "links": {
                    "🔗 Ver Merge Request": mr_link
                }
            }
            # Note: We do NOT transition the task status here, as per requirements.
            # It stays in 'In Review' until a human moves it.
            self.reporter.report_success(order.issue_key, report_payload)
            self.logger.info("Code review flow finished successfully.")

        except Exception as e:
            self.logger.exception("Critical error in Code Review")
            self.reporter.report_failure(order.issue_key, failure_reason=str(e))

    def _fetch_review_artifacts(self, order: CodeReviewOrder) -> Tuple[List[FileContentDTO], List[FileChangesDTO]]:
        """Fetches code context and diffs from VCS."""
        original_code = self.vcs.get_code_context(order.project_id, order.source_branch)
        changes = self.vcs.get_mr_changes(order.project_id, order.mr_id)
        return original_code, changes
