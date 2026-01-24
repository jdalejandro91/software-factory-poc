from dataclasses import dataclass
import logging

from software_factory_poc.application.core.domain.entities.scaffolding.scaffolding_agent_config import ScaffoldingAgentConfig
from software_factory_poc.application.core.domain.entities.scaffolding.scaffolding_request import ScaffoldingRequest

from software_factory_poc.application.core.domain.agents.capabilities.reporter_agent import ReporterAgent
from software_factory_poc.application.core.domain.agents.capabilities.vcs_agent import VcsAgent
from software_factory_poc.application.core.domain.agents.capabilities.research_agent import ResearchAgent
from software_factory_poc.application.core.domain.agents.capabilities.knowledge_agent import KnowledgeAgent
from software_factory_poc.application.core.domain.agents.capabilities.reasoning_agent import ReasoningAgent

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
        task_id = request.issue_key
        
        try:
            # Paso 1: Reportar inicio
            reporter.announce_start(task_id)

            # Paso 2: Verificar si la rama ya existe
            branch_name = f"feature/{request.issue_key}/scaffolding"
            existing_branch_url = vcs.branch_exists(request.repository_url, branch_name)
            
            if existing_branch_url:
                logger.info(f"Branch {branch_name} already exists. Skipping.")
                reporter.announce_redundancy(task_id, existing_branch_url)
                return

            # Paso 3: Investigación
            # Filtros basados en config (extra_params puede tener page_id, etc)
            search_filters = self.config.extra_params
            query = f"{request.technology_stack} {request.summary}"
            
            logger.info("Starting Research phase...")
            research_context = researcher.investigate(query, search_filters)

            # Paso 4: Conocimiento (RAG/Similares)
            logger.info("Retrieving Knowledge/Similar Solutions...")
            params_block = request.raw_instruction or "" 
            # Usamos raw instruction o summary para buscar similaridad
            knowledge_context = knowledge.retrieve_similar_solutions(params_block)

            # Acumular contexto
            full_context = f"Research Findings:\n{research_context}\n\nKnowledge Base:\n{knowledge_context}"

            # Paso 5: Razonamiento / Generación
            logger.info("Generating Scaffolding (Reasoning phase)...")
            generated_files = reasoner.generate_scaffolding(request, full_context)

            # Paso 6: Preparar VCS
            logger.info(f"Preparing workspace for {request.repository_url} on {branch_name}...")
            vcs.prepare_workspace(request.repository_url, branch_name)

            # Paso 7: Publicar cambios
            logger.info("Publishing changes...")
            mr_link = vcs.publish_changes(generated_files, f"Scaffolding for {request.issue_key}")

            # Paso 8: Reportar éxito
            reporter.announce_completion(task_id, mr_link)
            logger.info(f"Scaffolding flow completed successfully. MR: {mr_link}")

        except Exception as e:
            logger.error(f"Orchestration failed for {task_id}: {e}", exc_info=True)
            reporter.announce_failure(task_id, e)
            raise e
