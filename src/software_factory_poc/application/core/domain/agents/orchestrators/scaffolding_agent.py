from dataclasses import dataclass
import logging
from typing import List

from software_factory_poc.application.core.domain.entities.scaffolding.scaffolding_agent_config import ScaffoldingAgentConfig
from software_factory_poc.application.core.domain.entities.scaffolding.scaffolding_request import ScaffoldingRequest

from software_factory_poc.application.core.domain.agents.capabilities.reporter_agent import ReporterAgent
from software_factory_poc.application.core.domain.agents.capabilities.vcs_agent import VcsAgent
from software_factory_poc.application.core.domain.agents.capabilities.research_agent import ResearchAgent
from software_factory_poc.application.core.domain.agents.capabilities.knowledge_agent import KnowledgeAgent
from software_factory_poc.application.core.domain.agents.capabilities.reasoning_agent import ReasoningAgent
from software_factory_poc.application.core.ports.gateways.dtos import FileContent

logger = logging.getLogger(__name__)

@dataclass
class ScaffoldingAgent:
    """
    Orchestrator Agent for Scaffolding Tasks.
    Coordinates the capabilities: Research -> Reasoning -> Knowledge -> VCS -> Reporting.
    """
    config: ScaffoldingAgentConfig

    def execute_flow(
        self,
        request: ScaffoldingRequest,
        reporter: ReporterAgent,
        vcs: VcsAgent,
        researcher: ResearchAgent,
        reasoner: ReasoningAgent,
        knowledge: KnowledgeAgent
    ) -> None:
        """
        Executes the scaffolding orchestration flow.
        """
        try:
            # Step 1: Report Start
            reporter.announce_start(request.issue_key)
            
            # Step 2: Check Redundancy
            if self._check_redundancy(request, vcs, reporter):
                return
            
            # Step 3 & 4: Gather Context (Research + Knowledge)
            context = self._gather_context(request, researcher, knowledge)
            
            # Step 5: Reasoning (Generate Files)
            files = self._perform_reasoning(request, context, reasoner)
            
            # Step 6 & 7: Publish Results
            mr_link = self._publish_results(request, files, vcs)
            
            # Step 8: Success
            reporter.announce_completion(request.issue_key, mr_link)
            logger.info(f"Scaffolding flow completed successfully. MR: {mr_link}")

        except Exception as e:
            self._handle_failure(request.issue_key, e, reporter)

    def _check_redundancy(self, request: ScaffoldingRequest, vcs: VcsAgent, reporter: ReporterAgent) -> bool:
        branch_name = f"feature/{request.issue_key}/scaffolding"
        existing_branch_url = vcs.branch_exists(request.repository_url, branch_name)
        
        if existing_branch_url:
            logger.info(f"Branch {branch_name} already exists. Skipping.")
            reporter.announce_redundancy(request.issue_key, existing_branch_url)
            return True
        return False

    def _gather_context(self, request: ScaffoldingRequest, researcher: ResearchAgent, knowledge: KnowledgeAgent) -> str:
        # Step 3: Research
        search_filters = self.config.extra_params
        query = f"{request.technology_stack} {request.summary}"
        
        logger.info("Starting Research phase...")
        research_context = researcher.investigate(query, search_filters)

        # Step 4: Knowledge
        logger.info("Retrieving Knowledge/Similar Solutions...")
        params_block = request.raw_instruction or ""
        knowledge_context = knowledge.retrieve_similar_solutions(params_block)

        return f"Research Findings:\n{research_context}\n\nKnowledge Base:\n{knowledge_context}"

    def _perform_reasoning(self, request: ScaffoldingRequest, context: str, reasoner: ReasoningAgent) -> List[FileContent]:
        logger.info("Generating Scaffolding (Reasoning phase)...")
        return reasoner.generate_scaffolding(request, context)

    def _publish_results(self, request: ScaffoldingRequest, files: List[FileContent], vcs: VcsAgent) -> str:
        branch_name = f"feature/{request.issue_key}/scaffolding"
        
        logger.info(f"Preparing workspace for {request.repository_url} on {branch_name}...")
        vcs.prepare_workspace(request.repository_url, branch_name)
        
        logger.info("Publishing changes...")
        return vcs.publish_changes(files, f"Scaffolding for {request.issue_key}")

    def _handle_failure(self, task_id: str, error: Exception, reporter: ReporterAgent) -> None:
        logger.error(f"Orchestration failed for {task_id}: {error}", exc_info=True)
        reporter.announce_failure(task_id, error)
        # Re-raise to let upper layers (e.g. Workers) handle retry logic or DLQ
        raise error
