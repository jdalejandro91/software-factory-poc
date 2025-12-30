from typing import cast

from software_factory_poc.application.core.domain.configuration.scaffolding_agent_config import (
    ScaffoldingAgentConfig,
)
from software_factory_poc.application.core.domain.entities.scaffolding.scaffolding_request import (
    ScaffoldingRequest,
)
from software_factory_poc.application.core.domain.entities.task.task import Task
from software_factory_poc.application.core.domain.entities.scaffolding.scaffolding_agent import ScaffoldingAgent
from software_factory_poc.application.core.domain.services.file_parsing_service import (
    FileParsingService,
)
from software_factory_poc.application.core.ports.gateways.task_tracker_gateway_port import (
    TaskTrackerGatewayPort,
)
from software_factory_poc.application.core.domain.exceptions.domain_error import DomainError
from software_factory_poc.infrastructure.observability.logger_factory_service import (
    LoggerFactoryService,
)
from software_factory_poc.infrastructure.resolution.provider_resolver import ProviderResolver

logger = LoggerFactoryService.build_logger(__name__)


class CreateScaffoldingUseCase:
    """
    Orchestrator for the "Software Factory" scaffolding flow.
    Coordinates: Context Retrieval -> Planning -> Code Generation -> Parsing -> Version Control -> Notification.
    """
    def __init__(self, config: ScaffoldingAgentConfig, resolver: ProviderResolver):
        self.config = config
        self.resolver = resolver
        self.agent = ScaffoldingAgent()

    def execute(self, request: ScaffoldingRequest) -> None:
        logger.info(f"Starting scaffolding execution for issue: {request.issue_key}")
        
        # 1. Resolve Adapters
        vcs_gateway = self.resolver.resolve_vcs()
        # tracker_gateway must implement TaskTrackerGatewayPort. We assume resolve_tracker returns compatible adapter.
        tracker_gateway = cast(TaskTrackerGatewayPort, self.resolver.resolve_tracker())
        llm_gateway = self.resolver.resolve_llm_gateway()
        # knowledge_gateway = self.resolver.resolve_knowledge() # Helper/Impl pending
        
        # 0. Instanciar entidad Task
        task = Task(id=request.issue_key)

        try:
            # 1. Verificar si la rama ya existe (Ahorro de costos LLM)
            # Need to resolve project ID or use repository_url if it acts as ID/Path
            # The contract (ScaffoldingRequest) has repository_url. GitLab provider uses project path/id.
            # Assuming repository_url is the project path (e.g. "group/project")
            project_identifier = request.repository_url or "unknown/repo"
            
            # Resolve numeric ID if needed, standard implementations might handle path strings.
            # GitLabProvider usually has resolve_project_id.
            # Let's try to verify branch directly or via ID.
            project_id = vcs_gateway.resolve_project_id(project_identifier)
            
            # Use 'process_jira_request_usecase' style naming or 'naming_service'?
            # For this implementation we use standard naming convention directly here or via service.
            # User pseudocode: self.naming_service.generate_branch_name(request) - Skipping extra service for now unless requested.
            branch_name = f"feature/{request.issue_key}/scaffolding"
            
            if vcs_gateway.branch_exists(project_id, branch_name):
                # Escenario: RAMA EXISTENTE
                logger.info(f"Branch {branch_name} already exists. Skipping generation.")
                self.agent.report_existing_branch(task, branch_name, tracker_gateway)
                return

            # 2. Retrieve Context
            knowledge_gateway = self.resolver.resolve_knowledge()
            context = knowledge_gateway.retrieve_context(f"{request.technology_stack} {request.summary}")

            # 3. Construir Prompt y Llamar LLM
            prompt = self.agent.build_prompt(request, context)
            
            logger.info("Generating code via LLM Gateway...")
            llm_response = llm_gateway.generate_code(
                prompt=prompt,
                model=self.config.llm_priority_list[0] if self.config.llm_priority_list else "gpt-4-turbo"
            )

            # 4. Parsing y Validación
            logger.info("Parsing LLM response...")
            files = FileParsingService.parse_llm_response(llm_response)
            self.agent.validate_files(files) # Lanza DomainError si están vacíos

            # 5. Operación VCS (Commit/Push/MR)
            # Create branch
            vcs_gateway.create_branch(project_id, branch_name)
            
            # Convert files (list[FileContent]) to map if commit_files expects map, 
            # OR refactor ParseService/Gateway. 
            # Existing GitLabProvider.commit_files expects `files_map: dict[str, str]` (path -> content).
            files_map = {f.path: f.content for f in files}
            
            mr_title = f"Scaffolding for {request.issue_key}"
            
            vcs_gateway.commit_files(project_id, branch_name, files_map, f"feat: {mr_title}")
            
            # Create MR
            # GitLabProvider.create_merge_request returns dict usually containing 'web_url'.
            mr_result = vcs_gateway.create_merge_request(
                project_id=project_id,
                source_branch=branch_name,
                target_branch="main", # Default target
                title=mr_title,
                description=f"Automated scaffolding for {request.issue_key}"
            )
            mr_url = mr_result.get("web_url", "URL not found")

            # 6. Escenario: ÉXITO
            self.agent.report_success(task, mr_url, tracker_gateway)
            logger.info(f"Flow completed successfully for {request.issue_key}")

        except Exception as e:
            # 7. Escenario: FALLO
            logger.error(f"Scaffolding flow failed for {request.issue_key}: {e}", exc_info=True)
            self.agent.report_failure(task, error=e, gateway=tracker_gateway)
            # Opcional: Relanzar excepción si necesitamos que el endpoint HTTP retorne 500
            # User says: "Opcional... pero el negocio pide que la tarea quede actualizada."
            # We will NOT reraise to avoid 500 response if it was handled purely via async task business logic.
