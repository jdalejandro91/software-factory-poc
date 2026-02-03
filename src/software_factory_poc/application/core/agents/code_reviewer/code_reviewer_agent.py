from typing import List, Tuple, Dict, Any

from software_factory_poc.application.core.agents.base_agent import BaseAgent
from software_factory_poc.application.core.agents.code_reviewer.config.code_reviewer_agent_config import (
    CodeReviewerAgentConfig,
)
from software_factory_poc.application.core.agents.code_reviewer.dtos.code_review_result_dto import CodeReviewResultDTO
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
from software_factory_poc.application.core.domain.entities.task import Task
from software_factory_poc.infrastructure.observability.logger_factory_service import LoggerFactoryService

logger = LoggerFactoryService.build_logger(__name__)


class CodeReviewerAgent(BaseAgent):
    """
    Orchestrator Agent for Code Review Tasks.
    Refactored with Layered Research Strategy and Domain Task Entity.
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

    def execute_flow(self, task: Task) -> None:
        """
        Main orchestration flow for Code Review using Task Entity.
        """
        logger.info(f"Starting code review for Task {task.key}")
        
        try:
            self.reporter.report_start(task.key, message="🧐 Iniciando revisión de código...")

            # Extract Params from Task Config
            # Prioritize nested 'code_review_params', fallback to root for backward compatibility
            cr_params = task.description.config.get("code_review_params")
            if not cr_params:
                logger.info("No 'code_review_params' found. Falling back to root config.")
                cr_params = task.description.config
            
            # --- Robustness: Extract MR ID from URL if missing ---
            mr_id_raw = cr_params.get("mr_id") or cr_params.get("merge_request_id")
            review_url = cr_params.get("review_request_url")
            
            if not mr_id_raw and review_url:
                import re
                # Pattern for .../merge_requests/123 or .../merge_requests/123/...
                match = re.search(r"merge_requests/(\d+)", review_url)
                if match:
                    mr_iid = match.group(1)
                    logger.info(f"🔍 Extracted MR IID: {mr_iid} from URL: {review_url}")
                    cr_params["mr_id"] = mr_iid
                else:
                    logger.warning(f"Could not extract MR ID from URL: {review_url}")
            # -----------------------------------------------------
            
            # Phase 1: Validation
            if not self._validate_preconditions(task, cr_params):
                return

            # Phase 2: Data Gathering
            original_code, changes, continue_flow = self._fetch_and_validate_artifacts(task, cr_params)
            if not continue_flow:
                return

            # Execute Layered Research Strategy
            technical_context = self._gather_technical_context(task, cr_params)

            # Phase 3: Analysis (Reasoning)
            review_result = self._perform_review_reasoning(task, original_code, changes, technical_context)

            # Phase 4: Submission & Reporting
            self._submit_review_comments(task, cr_params, review_result)
            self._report_completion(task, cr_params, review_result)

        except Exception as e:
            self._handle_critical_failure(task, e)

    # --- Phase 1: Validation Methods ---

    def _validate_preconditions(self, task: Task, params: Dict[str, Any]) -> bool:
        project_id = params.get("gitlab_project_id") or params.get("project_id")
        mr_id = params.get("mr_id") or params.get("merge_request_id")
        
        # We can implement specific checks now
        # 1. Check ID existence
        if not project_id or not mr_id:
            msg = f"Missing Project ID ({project_id}) or MR ID ({mr_id}) in params."
            logger.error(msg)
            self.reporter.report_failure(task.key, msg)
            return False

        # 2. MR Existence Check
        exists = self.vcs.validate_mr(int(project_id), int(mr_id))
        if not exists:
            msg = f"Merge Request {mr_id} not found in project {project_id}"
            logger.error(msg)
            self.reporter.report_failure(task.key, msg)
            return False

        logger.info(f"MR {mr_id} validated. Proceeding...")
        return True

    # --- Phase 2: Data Gathering Methods ---

    def _fetch_and_validate_artifacts(
        self, task: Task, params: Dict[str, Any]
    ) -> Tuple[List[FileContentDTO], List[FileChangesDTO], bool]:
        """
        Fetches artifacts. Returns (OriginalCode, Changes, ShouldContinue).
        """
        project_id = int(params.get("gitlab_project_id") or params.get("project_id"))
        mr_id = int(params.get("mr_id") or params.get("merge_request_id"))
        source_branch = params.get("source_branch")
        
        # If source branch missing, maybe try to fetch MR info?
        # For now, let VCS agent handle default or fail.
        # Ideally MR fetch provides source branch. 
        # Assuming we just need changes mostly.
        
        # Fetch Changes
        changes = self.vcs.get_mr_changes(project_id, mr_id)

        if not changes:
            msg = "Review skipped: No changes detected in MR."
            logger.info(msg)
            self.reporter.report_success(task.key, msg)
            return [], [], False
            
        # Optimization: Fetch Original Context only for changed files?
        # The prompt builder logic implies it needs original files context.
        # VCS Agent `get_code_context` likely fetches main branch code or target.
        # Let's assume passed source_branch or default. 
        # If source_branch not in params, let's skip code context or fetch from MR target?
        # Keeping consistent with original logic:
        original_code = []
        if source_branch: 
            original_code = self.vcs.get_code_context(project_id, source_branch)

        return original_code, changes, True

    def _gather_technical_context(self, task: Task, params: Dict[str, Any]) -> str:
        """
        Layered Research Strategy.
        """
        context_parts = []
        
        service_name = params.get("service_name")
        technical_doc_id = params.get("technical_doc_id") or params.get("confluence_page_id")
        
        # 1. Project Context
        if service_name:
            logger.info(f"🔎 Researching Project Context for: '{service_name}'")
            try:
                project_ctx = self.researcher.research_project_technical_context(service_name)
                if project_ctx and "ERROR" not in project_ctx:
                    context_parts.append(f"=== REGLAS DEL PROYECTO ({service_name}) ===\n{project_ctx}")
            except Exception as e:
                logger.warning(f"Failed to retrieve project context: {e}")

        # 2. Specific Technical Doc
        if technical_doc_id:
            logger.info(f"🔎 Researching Specific Doc ID: {technical_doc_id}")
            try:
                doc_ctx = self.researcher.investigate(query="", specific_page_id=technical_doc_id)
                if doc_ctx:
                    context_parts.append(f"=== DOCUMENTACIÓN VINCULADA ===\n{doc_ctx}")
            except Exception as e:
                logger.warning(f"Failed to retrieve specific doc: {e}")

        # 3. Global/General Standards
        logger.info(f"🔎 Researching General Standards for: {task.summary}")
        query = f"Best practices, security, and clean code standards for {task.summary}"
        global_ctx = self.researcher.investigate(query=query)
        context_parts.append(f"=== ESTÁNDARES GENERALES Y BUENAS PRÁCTICAS ===\n{global_ctx}")

        full_context = "\n\n".join(context_parts)
        logger.info(f"Research complete. Total context size: {len(full_context)} chars")
        
        return full_context

    # --- Phase 3: Analysis Methods ---

    def _perform_review_reasoning(
        self,
        task: Task,
        original_code: List[FileContentDTO],
        changes: List[FileChangesDTO],
        context: str
    ) -> CodeReviewResultDTO:
        
        # Using raw_content as requirements description + summary
        requirements = f"{task.summary}\n\n{task.description.raw_content}"
        
        prompt = self.prompt_builder.build_prompt(
            diffs=changes,
            original_files=original_code,
            technical_context=context,
            requirements=requirements
        )
        logger.info("Prompt constructed successfully.")

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

    def _submit_review_comments(self, task: Task, params: Dict[str, Any], result: CodeReviewResultDTO) -> None:
        if not result.comments:
            logger.info("No comments generated by the reviewer.")
            return
            
        project_id = int(params.get("gitlab_project_id") or params.get("project_id"))
        mr_id = int(params.get("mr_id") or params.get("merge_request_id"))

        self.vcs.submit_review(project_id, mr_id, result.comments)
        logger.info("Review comments submitted to VCS.")

    def _report_completion(self, task: Task, params: Dict[str, Any], result: CodeReviewResultDTO) -> None:
        verdict_emoji = {
            "APPROVE": "✅",
            "COMMENT": "💬",
            "REQUEST_CHANGES": "🚫"
        }.get(result.verdict.name, "📋")

        # Robust URL extraction
        mr_url = params.get("review_request_url") or params.get("mr_url")
        if not mr_url:
             # Fallback: Construct URL or use generic (avoid failing reporting)
             logger.warning("MR URL missing in params.")
             mr_url = f"https://gitlab.com/projects/{params.get('project_id', 'unknown')}/merge_requests/{mr_id}" if mr_id else "https://gitlab.com"
        
        logger.info(f"🔗 Generando payload de éxito. URL del MR: '{mr_url}'")
        
        report_payload = {
            "type": "code_review_success",
            "title": f"Code Review Finalizado: {verdict_emoji} {result.verdict.name}",
            "summary": "Se completó la revisión de código. Los comentarios se publicaron en el MR.",
            "links": {
                "🔗 Ver Merge Request": mr_url
            }
        }
        
        self.reporter.report_success(task.key, report_payload)
        
        # 5. Update Task Metadata (Persist Review Status to YAML)
        from datetime import datetime
        
        review_context = {
            "review_status": {
                "last_review_at": datetime.utcnow().isoformat(),
                "status": result.verdict.name,
                "reviewer": "CodeReviewerAgent"
            }
        }
        
        # Merge into Task Config
        updated_task = task.update_metadata(review_context)
        logger.info(f"Updated Task Metadata with Review Status: {result.verdict.name}")
        
        # Sync with Jira (This ensures the YAML block in Description is updated)
        self.reporter.update_task_description(task.key, updated_task.description)
        
        logger.info("Code review flow finished successfully.")

    def _handle_critical_failure(self, task: Task, error: Exception) -> None:
        logger.exception("Critical error in Code Review")
        self.reporter.report_failure(task.key, error_msg=str(error))