import logging
import re
from dataclasses import dataclass, replace
from typing import List

from software_factory_poc.application.core.agents.base_agent import BaseAgent
from software_factory_poc.application.core.agents.common.config.task_status import TaskStatus
from software_factory_poc.application.core.agents.common.dtos.file_content_dto import FileContentDTO
from software_factory_poc.application.core.agents.reasoner.reasoner_agent import ReasonerAgent
from software_factory_poc.application.core.agents.reporter.reporter_agent import ReporterAgent
from software_factory_poc.application.core.agents.research.research_agent import ResearchAgent
from software_factory_poc.application.core.agents.scaffolding.scaffolding_contract import ScaffoldingContractModel
from software_factory_poc.application.core.agents.scaffolding.tools.artifact_parser import ArtifactParser
from software_factory_poc.application.core.agents.scaffolding.tools.scaffolding_prompt_builder import \
    ScaffoldingPromptBuilder
from software_factory_poc.application.core.agents.vcs.vcs_agent import VcsAgent
from .config.scaffolding_agent_config import ScaffoldingAgentConfig
from .value_objects.scaffolding_order import ScaffoldingOrder

logger = logging.getLogger(__name__)


@dataclass
class ScaffoldingAgent(BaseAgent):
    """
    Orchestrator Agent for Scaffolding Tasks.
    """
    config: ScaffoldingAgentConfig

    def __init__(self, config: ScaffoldingAgentConfig):
        super().__init__(name="ScaffoldingAgent", role="Orchestrator", goal="Orchestrate scaffolding creation")
        self.config = config
        self.prompt_builder_tool = ScaffoldingPromptBuilder()
        self.artifact_parser_tool = ArtifactParser()

    def execute_flow(
            self,
            request: ScaffoldingOrder,
            reporter: ReporterAgent,
            vcs: VcsAgent,
            researcher: ResearchAgent,
            reasoner: ReasonerAgent,
    ) -> None:
        try:
            reporter.report_start(request.issue_key)

            # STEP 1: PARSE CONTRACT
            try:
                contract = ScaffoldingContractModel.from_raw_text(request.raw_instruction)

                # Since ScaffoldingOrder is frozen, we must use replace() to create a new instance with the updated field.
                if contract.technology_stack:
                    logger.info(f"Override Tech Stack from Contract: {contract.technology_stack}")
                    request = replace(request, technology_stack=contract.technology_stack)

            except Exception as parse_error:
                logger.error(f"Contract parsing failed: {parse_error}")
                reporter.report_failure(request.issue_key, f"Invalid Contract: {parse_error}")
                return

            target_repo = self._resolve_target_repo(request, contract)
            project_id = vcs.resolve_project_id(target_repo)

            # STEP 2: SECURITY CHECK
            self._check_permissions(target_repo)

            # STEP 3: PRECONDITIONS
            if self._check_preconditions(request, vcs, reporter, target_repo):
                return

            # STEP 4: GENERATION
            artifacts = self._generate_scaffolding_artifacts(request, researcher, reasoner)

            # STEP 5: VCS OPERATIONS
            mr_link, branch_link, branch_name = self._apply_changes_to_vcs(request, vcs, artifacts, project_id)

            if not mr_link or not mr_link.startswith("http"):
                raise ValueError(f"Invalid MR Link generated: '{mr_link}'. Cannot complete task.")

            self._finalize_task_success(request, reporter, mr_link, project_id, branch_name)

        except Exception as e:
            self._handle_error(request, e, reporter)

    def _resolve_target_repo(self, request: ScaffoldingOrder, contract: ScaffoldingContractModel) -> str:
        if contract.gitlab.project_path:
            return contract.gitlab.project_path
        if contract.gitlab.project_id:
            return str(contract.gitlab.project_id)
        if request.repository_url:
            return request.repository_url
        raise ValueError("Target repository not found in Contract or Request.")

    def _check_preconditions(self, request: ScaffoldingOrder, vcs: VcsAgent, reporter: ReporterAgent,
                             target_repo: str) -> bool:
        project_id = vcs.resolve_project_id(target_repo)
        branch_name = self._get_branch_name(request)

        existing_url = vcs.validate_branch(project_id, branch_name, target_repo)

        if existing_url:
            self._handle_existing_branch(request, branch_name, existing_url, reporter)
            return True
        return False

    def _handle_existing_branch(self, request: ScaffoldingOrder, branch_name: str, existing_url: str,
                                reporter: ReporterAgent) -> None:
        from software_factory_poc.application.core.agents.reporter.config.reporter_constants import ReporterMessages
        reporter.report_success(
            request.issue_key,
            f"{ReporterMessages.BRANCH_EXISTS_PREFIX}{branch_name}|{existing_url}"
        )
        reporter.transition_task(request.issue_key, TaskStatus.IN_REVIEW)

    def _check_permissions(self, target_repo: str) -> None:
        if not self.config.project_allowlist:
            logger.warning("No allowlist configured. All groups allowed (INSECURE).")
            return

        group = target_repo.split("/")[0] if "/" in target_repo else target_repo

        if group not in self.config.project_allowlist:
            logger.warning(f"Security Block: Group '{group}' not in allowlist {self.config.project_allowlist}")
            raise PermissionError(f"Security Policy Violation: Group '{group}' is not authorized for scaffolding.")

    def _generate_scaffolding_artifacts(
            self,
            request: ScaffoldingOrder,
            researcher: ResearchAgent,
            reasoner: ReasonerAgent,
    ) -> List[FileContentDTO]:
        # Thanks to the replace(), request.technology_stack is now correctly updated (e.g. "TypeScript con NestJS")
        query = f"Architecture standards for {request.technology_stack} enterprise projects"

        logger.info(f"Researching: {query}")
        research_ctx = researcher.investigate(query)
        logger.info(f"Research result length: {len(research_ctx)}")

        full_context = f"Research:\n{research_ctx}"
        prompt = self.prompt_builder_tool.build_prompt(request, full_context)

        # --- MODEL SELECTION LOGIC ---
        model_id = self.config.model_name

        if not model_id and self.config.llm_model_priority:
            primary_model = self.config.llm_model_priority[0]
            model_id = f"{primary_model.provider.value}:{primary_model.name}"
            logger.info(f"Selected High Priority Model: {model_id}")

        if not model_id:
            model_id = "openai:gpt-4-turbo"
            logger.warning(f"No model configured. Falling back to default: {model_id}")

        raw_response = reasoner.reason(prompt, model_id)

        return self.artifact_parser_tool.parse_response(raw_response)

    def _apply_changes_to_vcs(self, request: ScaffoldingOrder, vcs: VcsAgent, artifacts: List[FileContentDTO],
                              project_id: int) -> tuple[str, str, str]:
        if not artifacts:
            raise ValueError("No artifacts generated to publish.")

        branch_name = self._get_branch_name(request)

        branch_dto = vcs.create_branch(project_id, branch_name, ref=self.config.default_target_branch)

        files_map = self._prepare_commit_payload(artifacts)
        vcs.commit_files(project_id, branch_name, files_map, f"Scaffolding for {request.issue_key}", force_create=False)

        mr = vcs.create_merge_request(
            project_id=project_id,
            source_branch=branch_name,
            title=f"Scaffolding {request.issue_key}",
            description=f"Auto-generated.\n{request.summary}",
            target_branch=self.config.default_target_branch
        )
        logger.info(f"MR Created successfully. Link: {mr.web_url}")
        )
        logger.info(f"MR Created successfully. Link: {mr.web_url}")
        return mr.web_url, branch_dto.web_url, branch_name

    def _get_branch_name(self, request: ScaffoldingOrder) -> str:
        safe_key = re.sub(r'[^a-z0-9\-]', '', request.issue_key.lower())
        return f"feature/{safe_key}-scaffolding"

    def _prepare_commit_payload(self, artifacts: List[FileContentDTO]) -> dict[str, str]:
        files_map = {}
        for artifact in artifacts:
            clean_path = artifact.path.lstrip("/")
            if clean_path in files_map:
                logger.warning(f"Duplicate path generated: {clean_path}. Overwriting.")
            files_map[clean_path] = artifact.content
        return files_map

    def _finalize_task_success(self, request: ScaffoldingOrder, reporter: ReporterAgent, mr_link: str,
                               project_id: int, branch_name: str) -> None:
        message_payload = {
            "type": "scaffolding_success",
            "title": "Scaffolding Completado Exitosamente",
            "summary": f"Se ha generado el código base para la tarea {request.issue_key}.\n{request.summary}",
            "links": {"🔗 Ver Merge Request": mr_link}
        }

        # Build Status Block for Code Review Agent
        from datetime import datetime
        automation_state = (
            f"\n\n```yaml\n"
            f"# --- AUTOMATION STATE (Machine Readable) ---\n"
            f"automation_result:\n"
            f"  gitlab_project_id: {project_id}\n"
            f"  source_branch_name: \"{branch_name}\"\n"
            f"  review_request_url: \"{mr_link}\"\n"
            f"  generated_at: \"{datetime.utcnow().isoformat()}\"\n"
            f"```"
        )
        
        # Inject into Jira Description as Single Source of Truth
        final_description = request.raw_instruction + automation_state
        reporter.update_task_description(request.issue_key, final_description)
        
        # Transition Issue
        reporter.report_success(request.issue_key, message_payload)
        reporter.transition_task(request.issue_key, TaskStatus.IN_REVIEW)
        logger.info(f"Task {request.issue_key} completed. MR: {mr_link}")

    def _handle_error(self, request: ScaffoldingOrder, error: Exception, reporter: ReporterAgent) -> None:
        logger.error(f"Task {request.issue_key} failed: {error}", exc_info=True)
        reporter.report_failure(request.issue_key, str(error))
        reporter.transition_task(request.issue_key, TaskStatus.TO_DO)
        logger.info(f"Error handled gracefully for task {request.issue_key}. Flow terminated.")