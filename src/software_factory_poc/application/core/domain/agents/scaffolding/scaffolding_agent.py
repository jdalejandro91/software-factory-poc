from dataclasses import dataclass
import logging
from typing import List

from .scaffolding_agent_config import ScaffoldingAgentConfig
from .scaffolding_order import ScaffoldingOrder
from software_factory_poc.application.core.domain.agents.common.config.task_status import TaskStatus

from software_factory_poc.application.core.domain.agents.reporter.reporter_agent import ReporterAgent
from software_factory_poc.application.core.domain.agents.vcs.vcs_agent import VcsAgent
from software_factory_poc.application.core.domain.agents.research.research_agent import ResearchAgent
from software_factory_poc.application.core.domain.agents.reasoner.reasoner_agent import ReasonerAgent
from software_factory_poc.application.core.domain.agents.scaffolding.tools.scaffolding_prompt_builder import ScaffoldingPromptBuilder
from software_factory_poc.application.core.domain.agents.scaffolding.tools.artifact_parser import ArtifactParser
from software_factory_poc.application.core.domain.agents.common.dtos.file_content_dto import FileContentDTO
from software_factory_poc.application.core.domain.agents.vcs.dtos.vcs_dtos import MergeRequestDTO

logger = logging.getLogger(__name__)

from software_factory_poc.application.core.domain.agents.base_agent import BaseAgent

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
        
        project_id = vcs.resolve_project_id(request.repository_url)
        branch_name = f"feature/{request.issue_key}/scaffolding"
        existing_url = vcs.check_branch_exists(project_id, branch_name, request.repository_url)
        
        if existing_url:
            msg = f"Branch exists: {existing_url}"
            reporter.report_success(request.issue_key, msg) # Using report_success as redundancy is a soft exit
            reporter.transition_task(request.issue_key, TaskStatus.IN_REVIEW)
            return True
        return False

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
        branch_name = f"feature/{request.issue_key}/scaffolding"
        
        vcs.create_branch(project_id, branch_name)
        
        files_map = {f.path: f.content for f in artifacts}
        vcs.commit_files(project_id, branch_name, files_map, f"Scaffolding for {request.issue_key}")
        
        mr = vcs.create_merge_request(
            project_id, branch_name, f"Scaffolding {request.issue_key}", f"Auto-generated.\n{request.summary}"
        )
        return mr.web_url

    def _finalize_task_success(self, request: ScaffoldingOrder, reporter: ReporterAgent, mr_link: str) -> None:
        reporter.report_success(request.issue_key, f"MR Created: {mr_link}")
        reporter.transition_task(request.issue_key, TaskStatus.IN_REVIEW)
        logger.info(f"Task {request.issue_key} completed. MR: {mr_link}")

    def _handle_error(self, request: ScaffoldingOrder, error: Exception, reporter: ReporterAgent) -> None:
        logger.error(f"Task {request.issue_key} failed: {error}", exc_info=True)
        reporter.report_failure(request.issue_key, str(error))
        reporter.transition_task(request.issue_key, TaskStatus.TO_DO)
        raise error
