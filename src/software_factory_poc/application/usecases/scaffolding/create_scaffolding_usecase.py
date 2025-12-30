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
        
        # 1. Asegurar canal de reporte (Jira) - PRIORIDAD 1
        try:
            # tracker_gateway must implement TaskTrackerGatewayPort. We assume resolve_tracker returns compatible adapter.
            tracker_gateway = cast(TaskTrackerGatewayPort, self.resolver.resolve_tracker())
        except Exception as e:
            # Si falla esto, estamos ciegos. Loguear CRITICAL y abortar.
            logger.critical(f"CRITICAL: Failed to resolve Tracker for {request.issue_key}. Cannot report failure: {e}", exc_info=True)
            return

        # 2. Instanciar entidad Task
        task = Task(id=request.issue_key)

        try:
            # 3. GLOBAL TRY-CATCH: Cualquier fallo aquí será reportado
            
            # Resolve Adapters (Aquí fallará si GitHub no está implementado)
            vcs_gateway = self.resolver.resolve_vcs()
            llm_gateway = self.resolver.resolve_llm_gateway()
            # knowledge_gateway = self.resolver.resolve_knowledge() # Resolved later when needed
            
            # 4. Verificar si la rama ya existe
            # Removing manual URL concatenation to support both IDs and raw paths
            project_identifier = request.repository_url or "unknown/repo"
            project_id = vcs_gateway.resolve_project_id(project_identifier)
            branch_name = f"feature/{request.issue_key}/scaffolding"
            
            if vcs_gateway.branch_exists(project_id, branch_name):
                logger.info(f"Branch {branch_name} already exists. Skipping generation.")
                self.agent.report_existing_branch(task, branch_name, tracker_gateway)
                return

            # 5. Retrieve Context via Agent
            knowledge_gateway = self.resolver.resolve_knowledge()
            
            # Construir filtros de búsqueda basados en la configuración
            # NO INCLUIR CREDENCIALES AQUÍ. El adaptador ya las tiene.
            search_filters = {
                "page_id": self.config.architecture_page_id,
                "query": f"{request.technology_stack} {request.summary}" # Fallback opcional
            }
            
            logger.info(f"Delegating knowledge search to Agent with filters: {search_filters}")
            context = self.agent.search_knowledge(knowledge_gateway, search_filters)
            
            # Mantener el log de debug del contenido (Core)
            print(f"\n🧠 [CORE:KNOWLEDGE] Received Context via Agent:\n"
                  f"--------------------------------------------------\n"
                  f"{context}\n"
                  f"--------------------------------------------------\n", flush=True)

            # 6. Construir Prompt y Llamar LLM
            # prompt now returns a single string (System + User combined) or we can split if Gateway supports it.
            # Current `LlmGateway.generate_code` takes `prompt: str`.
            # So we pass the full constructed prompt.
            full_prompt = self.agent.build_prompt(request, context)
            
            logger.info("Generating code via LLM Gateway...")
            llm_response = llm_gateway.generate_code(
                prompt=full_prompt,
                model=self.config.llm_model_priority[0].name if self.config.llm_model_priority else "gpt-4-turbo"
            )

            # 7. Parsing y Validación
            logger.info("Parsing LLM response...")
            files = FileParsingService.parse_llm_response(llm_response)
            self.agent.validate_files(files) # Lanza DomainError si están vacíos

            # 8. Operación VCS (Commit/Push/MR)
            vcs_gateway.create_branch(project_id, branch_name)
            
            files_map = {f.path: f.content for f in files}
            mr_title = f"Scaffolding for {request.issue_key}"
            
            vcs_gateway.commit_files(project_id, branch_name, files_map, f"feat: {mr_title}")
            
            mr_result = vcs_gateway.create_merge_request(
                project_id=project_id,
                source_branch=branch_name,
                target_branch="main", 
                title=mr_title,
                description=f"Automated scaffolding for {request.issue_key}"
            )
            mr_url = mr_result.get("web_url", "URL not found")

            # 9. Escenario: ÉXITO
            self.agent.report_success(task, mr_url, tracker_gateway)
            logger.info(f"Flow completed successfully for {request.issue_key}")

        except Exception as e:
            # 10. Escenario: FALLO (Reportado a Jira)
            logger.error(f"Scaffolding flow failed for {request.issue_key}: {e}", exc_info=True)
            # Gracias al paso 1, tenemos tracker_gateway seguro para reportar
            self.agent.report_failure(task, error=e, gateway=tracker_gateway)
