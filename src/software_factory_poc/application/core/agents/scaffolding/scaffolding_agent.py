from dataclasses import dataclass
import logging
import re
from typing import List

from .config.scaffolding_agent_config import ScaffoldingAgentConfig
from .value_objects.scaffolding_order import ScaffoldingOrder
from software_factory_poc.application.core.agents.common.config.task_status import TaskStatus

from software_factory_poc.application.core.agents.reporter.reporter_agent import ReporterAgent
from software_factory_poc.application.core.agents.vcs.vcs_agent import VcsAgent
from software_factory_poc.application.core.agents.research.research_agent import ResearchAgent
from software_factory_poc.application.core.agents.reasoner.reasoner_agent import ReasonerAgent
from software_factory_poc.application.core.agents.scaffolding.tools.scaffolding_prompt_builder import ScaffoldingPromptBuilder
from software_factory_poc.application.core.agents.scaffolding.tools.artifact_parser import ArtifactParser
from software_factory_poc.application.core.agents.common.dtos.file_content_dto import FileContentDTO


logger = logging.getLogger(__name__)

from software_factory_poc.application.core.agents.base_agent import BaseAgent

@dataclass
class ScaffoldingAgent(BaseAgent):
    """
    Orchestrator Agent for Scaffolding Tasks.
    Coordinates the capabilities: Research -> Reasoning -> Knowledge -> VCS -> Reporting.
    """
    config: ScaffoldingAgentConfig

    def __init__(self, config: ScaffoldingAgentConfig):
        super().__init__(name="ScaffoldingAgent", role="Orchestrator", goal="Orchestrate scaffolding creation")
        self.config = config
        # Instantiate Tools
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
        """Executes the scaffolding orchestration flow."""
        try:
            if self._start_task_execution(request, reporter, vcs):
                return

            artifacts = self._generate_scaffolding_artifacts(request, researcher, reasoner)
            mr_link = self._apply_changes_to_vcs(request, vcs, artifacts)
            
            self._finalize_task_success(request, reporter, mr_link)

        except Exception as e:
            self._handle_error(request, e, reporter)

    def _start_task_execution(self, request: ScaffoldingOrder, reporter: ReporterAgent, vcs: VcsAgent) -> bool:
        reporter.report_start(request.issue_key)
        
        self._check_permissions(request)

        
        # Extracted Precondition Check
        if self._check_preconditions(request, vcs, reporter):
            return True
            
        return False

    def _check_preconditions(self, request: ScaffoldingOrder, vcs: VcsAgent, reporter: ReporterAgent) -> bool:
        project_id = vcs.resolve_project_id(request.repository_url)
        branch_name = self._get_branch_name(request)
        
        # User requested method name
        existing_url = vcs.validate_branch(project_id, branch_name, request.repository_url)
        
        if existing_url:
            # Short-Circuit: Report as Info/Success but stop execution
            reporter.report_success(request.issue_key, f"ℹ️ BRANCH_EXISTS|{branch_name}|{existing_url}")
            reporter.transition_task(request.issue_key, TaskStatus.IN_REVIEW)
            return True
        return False

    def _check_permissions(self, request: ScaffoldingOrder) -> None:
        """
        Enforces security policy based on Allowlisted Groups.
        extracts path from raw_instruction using regex if not present in request.
        """
        if not self.config.project_allowlist:
            logger.warning("No allowlist configured. All groups allowed (INSECURE).")
            return

        # Attempt to extract path from raw_instruction (YAML block)
        # Looking for: gitlab_project_path: 'group/project'
        path = ""
        # 1. Try ScaffoldingOrder field if it existed (it does not currently, but defensive coding)
        if hasattr(request, "target_conf") and request.target_conf:
             path = request.target_conf.gitlab_project_path

        # 2. Regex fallback
        if not path:
             match = re.search(r"gitlab_project_path:\s*['\"]?([\w\-\./]+)['\"]?", request.raw_instruction)
             if match:
                 path = match.group(1)
        
        if not path:
             # If we can't find the target, we can't allowlist it.
             # Failing open or closed? Closed is secure.
             msg = "Could not identify 'gitlab_project_path' in instruction to validate permissions."
             logger.error(msg)
             raise ValueError(msg)
            
        group = path.split("/")[0]
        
        if group not in self.config.project_allowlist:
            logger.warning(f"Security Block: Group '{group}' not in allowlist {self.config.project_allowlist}")
            raise PermissionError(f"Security Policy Violation: Group '{group}' is not authorized for scaffolding.")


    def _generate_scaffolding_artifacts(
        self, 
        request: ScaffoldingOrder, 
        researcher: ResearchAgent, 
        reasoner: ReasonerAgent, 
    ) -> List[FileContentDTO]:
        query = f"Busca los lineamientos de arquitectura en la documentación oficial para la tecnología {request.technology_stack}"
        research_ctx = researcher.investigate(query)
        # Knowledge retrieval merged into research or just removed if redundant
        
        full_context = f"Research:\n{research_ctx}"
        prompt = self.prompt_builder_tool.build_prompt(request, full_context)
        
        model_id = self.config.model_name or "gpt-4-turbo"
        raw_response = reasoner.reason(prompt, model_id)
        
        return self.artifact_parser_tool.parse_response(raw_response)

    def _apply_changes_to_vcs(self, request: ScaffoldingOrder, vcs: VcsAgent, artifacts: List[FileContentDTO]) -> str:
        if not artifacts:
            raise ValueError("No artifacts generated to publish.")

        project_id = vcs.resolve_project_id(request.repository_url)
        branch_name = self._get_branch_name(request)
        
        vcs.create_branch(project_id, branch_name)
        
        files_map = self._prepare_commit_payload(artifacts)
        vcs.commit_files(project_id, branch_name, files_map, f"Scaffolding for {request.issue_key}")
        
        mr = vcs.create_merge_request(
            project_id=project_id, 
            source_branch=branch_name, 
            title=f"Scaffolding {request.issue_key}", 
            description=f"Auto-generated.\n{request.summary}",
            target_branch=self.config.default_target_branch
        )
        return mr.web_url

    def _get_branch_name(self, request: ScaffoldingOrder) -> str:
        return f"feature/{request.issue_key}-scaffolding"

    def _prepare_commit_payload(self, artifacts: List[FileContentDTO]) -> dict[str, str]:
        """
        Converts artifacts to VCS-ready dictionary.
        Sanitizes paths to ensure they are relative.
        """
        files_map = {}
        for artifact in artifacts:
            # Sanitize: Strip leading slash
            clean_path = artifact.path.lstrip("/")
            
            # Integrity Check: duplications? 
            # (Last write wins is standard, but maybe warn?)
            files_map[clean_path] = artifact.content
            
        return files_map

    def _finalize_task_success(self, request: ScaffoldingOrder, reporter: ReporterAgent, mr_link: str) -> None:
        message = f"Scaffolding completed via [MR Link]({mr_link})"
        reporter.report_success(request.issue_key, message)
        reporter.transition_task(request.issue_key, TaskStatus.IN_REVIEW)
        logger.info(f"Task {request.issue_key} completed. MR: {mr_link}")

    def _handle_error(self, request: ScaffoldingOrder, error: Exception, reporter: ReporterAgent) -> None:
        logger.error(f"Task {request.issue_key} failed: {error}", exc_info=True)
        reporter.report_failure(request.issue_key, str(error))
        reporter.transition_task(request.issue_key, TaskStatus.TO_DO)
        raise error
