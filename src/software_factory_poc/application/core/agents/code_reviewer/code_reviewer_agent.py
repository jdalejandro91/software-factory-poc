import logging
from typing import List, Optional, Tuple

from software_factory_poc.application.core.agents.base_agent import BaseAgent
from software_factory_poc.application.core.agents.code_reviewer.config.code_reviewer_agent_config import (
    CodeReviewerAgentConfig,
)
from software_factory_poc.application.core.agents.code_reviewer.dtos.code_review_result_dto import CodeReviewResultDTO
from software_factory_poc.application.core.agents.code_reviewer.tools.code_review_prompt_builder import (
    CodeReviewPromptBuilder,
)
from software_factory_poc.application.core.agents.code_reviewer.tools.review_result_parser import ReviewResultParser
from software_factory_poc.application.core.agents.code_reviewer.value_objects.code_review_order import (
    CodeReviewOrder,
)
from software_factory_poc.application.core.agents.common.dtos.file_changes_dto import FileChangesDTO
from software_factory_poc.application.core.agents.common.dtos.file_content_dto import FileContentDTO
from software_factory_poc.application.core.agents.reasoner.reasoner_agent import ReasonerAgent
from software_factory_poc.application.core.agents.reporter.reporter_agent import ReporterAgent
from software_factory_poc.application.core.agents.research.research_agent import ResearchAgent
from software_factory_poc.application.core.agents.vcs.vcs_agent import VcsAgent
from software_factory_poc.infrastructure.observability.logger_factory_service import LoggerFactoryService

logger = LoggerFactoryService.build_logger(__name__)


class CodeReviewerAgent(BaseAgent):
    """
    Orchestrator Agent for Code Review Tasks.
    Refactored with Layered Research Strategy.
    """

    def __init__(
        self,
        config: CodeReviewerAgentConfig,
        reporter: ReporterAgent,
        vcs: VcsAgent,
        researcher: ResearchAgent,
        reasoner: ReasonerAgent,
    ):
        super().__init__(name="CodeReviewerAgent", role="Reviewer", goal="Perform automated code reviews")
        
        # Dependencies (Composition)
        self.config = config
        self.reporter = reporter
        self.vcs = vcs
        self.researcher = researcher
        self.reasoner = reasoner

        # Internal Tools
        self.prompt_builder = CodeReviewPromptBuilder()
        self.parser = ReviewResultParser()
        
        logger.info("CodeReviewerAgent initialized")

    def execute_flow(self, order: CodeReviewOrder) -> None:
        """
        Main orchestration flow for Code Review.
        """
        self.logger.info(f"Starting code review for {order}")
        
        try:
            self.reporter.report_start(order.issue_key, message="🧐 Iniciando revisión de código...")

            # Phase 1: Validation
            if not self._validate_preconditions(order):
                return

            # Phase 2: Data Gathering
            original_code, changes, continue_flow = self._fetch_and_validate_artifacts(order)
            if not continue_flow:
                return

            # Execute Layered Research Strategy
            technical_context = self._gather_technical_context(order)

            # Phase 3: Analysis (Reasoning)
            review_result = self._perform_review_reasoning(order, original_code, changes, technical_context)

            # Phase 4: Submission & Reporting
            self._submit_review_comments(order, review_result)
            self._report_completion(order, review_result)

        except Exception as e:
            self._handle_critical_failure(order, e)

    # --- Phase 1: Validation Methods ---

    def _validate_preconditions(self, order: CodeReviewOrder) -> bool:
        # 1. Provider Check
        if order.vcs_provider.upper() != "GITLAB":
            msg = f"Provider '{order.vcs_provider}' not supported yet. Only GITLAB is supported."
            logger.warning(msg)
            self.reporter.report_failure(order.issue_key, msg)
            return False

        # 2. MR Existence Check
        exists = self.vcs.validate_mr(order.project_id, order.mr_id)
        if not exists:
            msg = f"Merge Request {order.mr_id} not found in project {order.project_id}"
            logger.error(msg)
            self.reporter.report_failure(order.issue_key, msg)
            return False

        logger.info(f"MR {order.mr_id} validated. Proceeding...")
        return True

    # --- Phase 2: Data Gathering Methods ---

    def _fetch_and_validate_artifacts(
        self, order: CodeReviewOrder
    ) -> Tuple[List[FileContentDTO], List[FileChangesDTO], bool]:
        """
        Fetches artifacts. Returns (OriginalCode, Changes, ShouldContinue).
        """
        original_code = self.vcs.get_code_context(order.project_id, order.source_branch)
        changes = self.vcs.get_mr_changes(order.project_id, order.mr_id)

        if not changes:
            msg = "Review skipped: No changes detected in MR."
            logger.info(msg)
            self.reporter.report_success(order.issue_key, msg)
            return [], [], False

        return original_code, changes, True

    def _gather_technical_context(self, order: CodeReviewOrder) -> str:
        """
        Executes a Layered Research Strategy similar to ScaffoldingAgent.
        1. Project Specific Context (via service_name)
        2. Specific Documentation (via technical_doc_id)
        3. Global Standards/Best Practices (Fallback/Supplement)
        """
        context_parts = []
        
        # 1. Project Context (High Priority)
        # Nota: Asumimos que 'service_name' viene en el order (ej. extraído de params de Jira)
        if order.service_name:
            logger.info(f"🔎 Researching Project Context for: '{order.service_name}'")
            try:
                project_ctx = self.researcher.research_project_technical_context(order.service_name)
                if project_ctx and "ERROR" not in project_ctx:
                    context_parts.append(f"=== REGLAS DEL PROYECTO ({order.service_name}) ===\n{project_ctx}")
            except Exception as e:
                logger.warning(f"Failed to retrieve project context: {e}")

        # 2. Specific Technical Doc (If linked in the Jira Task)
        if order.technical_doc_id:
            logger.info(f"🔎 Researching Specific Doc ID: {order.technical_doc_id}")
            try:
                doc_ctx = self.researcher.investigate(query="", specific_page_id=order.technical_doc_id)
                if doc_ctx:
                    context_parts.append(f"=== DOCUMENTACIÓN VINCULADA ===\n{doc_ctx}")
            except Exception as e:
                logger.warning(f"Failed to retrieve specific doc: {e}")

        # 3. Global/General Standards (Always include as baseline)
        logger.info(f"🔎 Researching General Standards for: {order.summary}")
        query = f"Best practices, security, and clean code standards for {order.summary}"
        global_ctx = self.researcher.investigate(query=query)
        context_parts.append(f"=== ESTÁNDARES GENERALES Y BUENAS PRÁCTICAS ===\n{global_ctx}")

        full_context = "\n\n".join(context_parts)
        logger.info(f"Research complete. Total context size: {len(full_context)} chars")
        
        return full_context

    # --- Phase 3: Analysis Methods ---

    def _perform_review_reasoning(
        self,
        order: CodeReviewOrder,
        original_code: List[FileContentDTO],
        changes: List[FileChangesDTO],
        context: str
    ) -> CodeReviewResultDTO:
        
        prompt = self.prompt_builder.build_prompt(
            diffs=changes,
            original_files=original_code,
            technical_context=context,
            requirements=f"{order.summary}\n\n{order.description}"
        )
        logger.info("Prompt constructed successfully.")

        # Resolve Model ID (using priority list or default)
        model_id = self.config.llm_model_priority if self.config.llm_model_priority else "openai:gpt-4-turbo"

        raw_response = self.reasoner.reason(
            prompt=prompt,
            model_id=model_id
        )
        logger.info(f"LLM response received. Length: {len(raw_response)} chars")

        review_result = self.parser.parse(raw_response)
        logger.info(f"Review parsed. Verdict: {review_result.verdict}. Comments: {len(review_result.comments)}")
        
        return review_result

    # --- Phase 4: Submission & Reporting Methods ---

    def _submit_review_comments(self, order: CodeReviewOrder, result: CodeReviewResultDTO) -> None:
        if not result.comments:
            logger.info("No comments generated by the reviewer.")
            return

        self.vcs.submit_review(order.project_id, order.mr_id, result.comments)
        logger.info("Review comments submitted to VCS.")

    def _report_completion(self, order: CodeReviewOrder, result: CodeReviewResultDTO) -> None:
        verdict_emoji = {
            "APPROVE": "✅",
            "COMMENT": "💬",
            "REQUEST_CHANGES": "🚫"
        }.get(result.verdict.name, "📋")

        mr_link = order.mr_url or f"MR ID: {order.mr_id}"
        
        report_payload = {
            "type": "code_review_completion",
            "title": f"Code Review Finalizado: {verdict_emoji} {result.verdict.name}",
            "summary": "Se completó la revisión de código. Los comentarios se publicaron en el MR.",
            "links": {
                "🔗 Ver Merge Request": mr_link
            }
        }
        
        # Note: Status remains 'In Review' as per requirements.
        self.reporter.report_success(order.issue_key, report_payload)
        logger.info("Code review flow finished successfully.")

    def _handle_critical_failure(self, order: CodeReviewOrder, error: Exception) -> None:
        logger.exception("Critical error in Code Review")
        self.reporter.report_failure(order.issue_key, error_msg=str(error))