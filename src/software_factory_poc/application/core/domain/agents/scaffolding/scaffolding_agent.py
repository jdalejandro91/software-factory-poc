from dataclasses import dataclass
import logging
from typing import List

from .scaffolding_agent_config import ScaffoldingAgentConfig
from .scaffolding_order import ScaffoldingOrder

from software_factory_poc.application.core.domain.agents.reporter.reporter_agent import ReporterAgent
from software_factory_poc.application.core.domain.agents.vcs.vcs_agent import VcsAgent
from software_factory_poc.application.core.domain.agents.research.research_agent import ResearchAgent
from software_factory_poc.application.core.domain.agents.knowledge.knowledge_agent import KnowledgeAgent
from software_factory_poc.application.core.domain.agents.reasoner.reasoner_agent import ReasonerAgent
from software_factory_poc.application.core.ports.gateways.dtos import FileContent

logger = logging.getLogger(__name__)

from software_factory_poc.application.core.domain.agents.base_agent import BaseAgent

@dataclass
class ScaffoldingAgent(BaseAgent):
    """
    Orchestrator Agent for Scaffolding Tasks.
    Coordinates the capabilities: Research -> Reasoning -> Knowledge -> VCS -> Reporting.
    """
    config: ScaffoldingAgentConfig
    # Providing defaults to satisfy dataclass inheritance without changing __init__ signature excessively
    # Note: In Python dataclasses, fields with defaults must follow fields without defaults.
    # BaseAgent has no defaults. If we rely on dataclass generation, we'd need to pass name/role/goal.
    # To avoid breaking callers, we'll assign them via field defaults or post_init, but strictly 
    # the cleanest way while keeping @dataclass might be to use kw_only=True if allowed or manual init.
    # Given constraints, we will convert this to a standard class inheriting from the dataclass to customize init,
    # OR simpler: use default values for the base fields here if python allows overriding.
    # Let's use the manual __init__ approach by removing @dataclass from this class but keeping inheritance.
    
    def __init__(self, config: ScaffoldingAgentConfig):
        super().__init__(name="ScaffoldingAgent", role="Orchestrator", goal="Orchestrate scaffolding creation")
        self.config = config

    def execute_flow(
        self,
        request: ScaffoldingOrder,
        reporter: ReporterAgent,
        vcs: VcsAgent,
        researcher: ResearchAgent,
        reasoner: ReasonerAgent,
        knowledge: KnowledgeAgent
    ) -> None:
        """
        Executes the scaffolding orchestration flow.
        """
        try:
            self._announce_task_start(request, reporter)
            
            if self._verify_redundancy(request, vcs, reporter):
                return

            research_context = self._conduct_research(request, researcher)
            knowledge_context = self._consult_knowledge_base(request, knowledge)
            full_context = self._consolidate_context(research_context, knowledge_context)
            
            artifacts = self._generate_code_artifacts(request, full_context, reasoner)
            
            mr_link = self._publish_to_vcs(request, artifacts, vcs)
            
            self._finalize_task(request, mr_link, reporter)

        except Exception as e:
            self._handle_error(request, e, reporter)

    def _announce_task_start(self, request: ScaffoldingOrder, reporter: ReporterAgent) -> None:
        reporter.announce_start(request.issue_key)

    def _verify_redundancy(self, request: ScaffoldingOrder, vcs: VcsAgent, reporter: ReporterAgent) -> bool:
        branch_name = f"feature/{request.issue_key}/scaffolding"
        existing_branch_url = vcs.branch_exists(request.repository_url, branch_name)
        
        if existing_branch_url:
            logger.info(f"Branch {branch_name} already exists. Skipping.")
            reporter.announce_redundancy(request.issue_key, existing_branch_url)
            return True
        return False

    def _conduct_research(self, request: ScaffoldingOrder, researcher: ResearchAgent) -> str:
        search_filters = self.config.extra_params
        query = f"{request.technology_stack} {request.summary}"
        
        logger.info("Starting Research phase...")
        return researcher.investigate(query, search_filters)

    def _consult_knowledge_base(self, request: ScaffoldingOrder, knowledge: KnowledgeAgent) -> str:
        logger.info("Retrieving Knowledge/Similar Solutions...")
        params_block = request.raw_instruction or ""
        return knowledge.retrieve_similar_solutions(params_block)

    def _consolidate_context(self, research: str, knowledge: str) -> str:
        return f"Research Findings:\n{research}\n\nKnowledge Base:\n{knowledge}"

    def _generate_code_artifacts(self, request: ScaffoldingOrder, context: str, reasoner: ReasonerAgent) -> List[FileContent]:
        logger.info("Generating Scaffolding (Reasoning phase)...")
        return reasoner.generate_scaffolding(request, context)

    def _publish_to_vcs(self, request: ScaffoldingOrder, files: List[FileContent], vcs: VcsAgent) -> str:
        branch_name = f"feature/{request.issue_key}/scaffolding"
        
        logger.info(f"Preparing workspace for {request.repository_url} on {branch_name}...")
        vcs.prepare_workspace(request.repository_url, branch_name)
        
        logger.info("Publishing changes...")
        return vcs.publish_changes(files, f"Scaffolding for {request.issue_key}")

    def _finalize_task(self, request: ScaffoldingOrder, mr_link: str, reporter: ReporterAgent) -> None:
        reporter.announce_completion(request.issue_key, mr_link)
        logger.info(f"Scaffolding flow completed successfully. MR: {mr_link}")

    def _handle_error(self, request: ScaffoldingOrder, error: Exception, reporter: ReporterAgent) -> None:
        task_id = request.issue_key
        logger.error(f"Orchestration failed for {task_id}: {error}", exc_info=True)
        reporter.announce_failure(task_id, error)
        raise error
