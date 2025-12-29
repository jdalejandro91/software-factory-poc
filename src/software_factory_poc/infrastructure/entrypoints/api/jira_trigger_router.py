from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, Security, status
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader

from software_factory_poc.application.usecases.knowledge.architecture_knowledge_service import (
    ArchitectureKnowledgeService,
)
from software_factory_poc.application.usecases.orchestration.scaffold_orchestrator_service import (
    ScaffoldOrchestratorService,
)
from software_factory_poc.application.usecases.scaffolding.genai_scaffolding_service import (
    GenaiScaffoldingService,
)
from software_factory_poc.configuration.main_settings import Settings
from software_factory_poc.application.core.entities.artifact_result import (
    ArtifactResultModel,
    ArtifactRunStatusEnum,
)
from software_factory_poc.application.core.services.scaffolding_contract_parser_service import (
    ScaffoldingContractParserService,
)
from software_factory_poc.infrastructure.providers.tools.confluence.clients.confluence_http_client import (
    ConfluenceHttpClient,
)
from software_factory_poc.infrastructure.providers.tools.confluence.confluence_provider_impl import (
    ConfluenceProviderImpl,
)
from software_factory_poc.infrastructure.providers.tools.gitlab.clients.gitlab_http_client import (
    GitLabHttpClient,
)
from software_factory_poc.infrastructure.providers.tools.gitlab.gitlab_provider_impl import (
    GitLabProviderImpl,
)
from software_factory_poc.infrastructure.providers.tools.gitlab.mappers.gitlab_payload_builder_service import (
    GitLabPayloadBuilderService,
)
from software_factory_poc.infrastructure.providers.tools.jira.clients.jira_http_client import (
    JiraHttpClient,
)
from software_factory_poc.infrastructure.entrypoints.api.dtos.jira_webhook_dto import JiraWebhookDTO
from software_factory_poc.infrastructure.entrypoints.api.mappers.jira_mapper import JiraMapper
from software_factory_poc.infrastructure.providers.tools.jira.jira_provider_impl import (
    JiraProviderImpl,
)
from software_factory_poc.infrastructure.providers.tools.jira.mappers.jira_issue_mapper_service import (
    JiraIssueMapperService,
)
from software_factory_poc.infrastructure.repositories.idempotency_key_builder_service import (
    IdempotencyKeyBuilderService,
)
from software_factory_poc.infrastructure.repositories.idempotency_store_file_adapter import (
    IdempotencyStoreFileAdapter,
)
from software_factory_poc.infrastructure.repositories.run_result_store_file_adapter import (
    RunResultStoreFileAdapter,
)
from software_factory_poc.infrastructure.observability.logger_factory_service import build_logger
from software_factory_poc.application.usecases.orchestration.step_runner_service import StepRunnerService
from software_factory_poc.application.core.policies.poc_policy_service import PocPolicyService
from software_factory_poc.infrastructure.providers.llms.facade.llm_bridge import LlmBridge

logger = build_logger(__name__)
router = APIRouter()

# Definimos que esperamos un header llamado "X-API-Key"
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

@lru_cache
def get_settings() -> Settings:
    return Settings()

async def verify_api_key(
    api_key: str = Security(api_key_header), 
    settings: Settings = Depends(get_settings)
):
    if not api_key:
        raise HTTPException(status_code=403, detail="Missing X-API-Key header")
    
    # Validamos contra el secreto configurado en Settings
    if api_key != settings.jira_webhook_secret.get_secret_value():
        raise HTTPException(status_code=403, detail="Invalid API Key")
    
    return api_key

def get_orchestrator(settings: Settings = Depends(get_settings)) -> ScaffoldOrchestratorService:
    # 1. Observability
    step_runner = StepRunnerService()

    # 2. Integrations
    jira_http = JiraHttpClient(settings)
    jira_client = JiraProviderImpl(jira_http)
    
    jira_mapper = JiraIssueMapperService()
    
    payload_builder = GitLabPayloadBuilderService()
    
    gitlab_http = GitLabHttpClient(settings)
    gitlab_client = GitLabProviderImpl(gitlab_http, payload_builder)

    confluence_http = ConfluenceHttpClient(settings)
    confluence_provider = ConfluenceProviderImpl(confluence_http)

    # 3. Core Domain & Knowledge
    contract_parser = ScaffoldingContractParserService()
    policy_service = PocPolicyService(settings)

    arch_service = ArchitectureKnowledgeService(confluence_provider, settings)
    
    # 4. AI / Scaffolding Engine
    llm_bridge = LlmBridge.from_settings(settings)
    # Injecting the Gateway as the LlmProvider
    genai_service = GenaiScaffoldingService(llm_bridge.gateway, arch_service)

    # 5. Persistence
    idempotency_builder = IdempotencyKeyBuilderService()
    idempotency_store = IdempotencyStoreFileAdapter(settings)
    run_result_store = RunResultStoreFileAdapter(settings)

    return ScaffoldOrchestratorService(
        settings=settings,
        step_runner=step_runner,
        jira_client=jira_client,
        jira_mapper=jira_mapper,
        contract_parser=contract_parser,
        genai_service=genai_service,
        policy_service=policy_service,
        gitlab_client=gitlab_client,
        idempotency_builder=idempotency_builder,
        idempotency_store=idempotency_store,
        run_result_store=run_result_store,
    )

from software_factory_poc.application.usecases.scaffolding.process_jira_request_usecase import ProcessJiraRequestUseCase
from software_factory_poc.infrastructure.providers.knowledge.confluence_mock_adapter import ConfluenceMockAdapter
from software_factory_poc.infrastructure.providers.llms.llm_gateway_adapter import LlmGatewayAdapter
from software_factory_poc.application.core.entities.scaffolding_agent import ScaffoldingAgent

def get_usecase(settings: Settings = Depends(get_settings)) -> ProcessJiraRequestUseCase:
    # Adapters
    kb_adapter = ConfluenceMockAdapter()
    
    llm_bridge = LlmBridge.from_settings(settings)
    llm_adapter = LlmGatewayAdapter(llm_bridge)

    # Providers
    jira_http = JiraHttpClient(settings)
    jira_provider = JiraProviderImpl(jira_http)

    gitlab_http = GitLabHttpClient(settings)
    payload_builder = GitLabPayloadBuilderService()
    gitlab_provider = GitLabProviderImpl(gitlab_http, payload_builder)
    
    # Agent
    agent = ScaffoldingAgent(llm_gateway=llm_adapter, knowledge_port=kb_adapter)
    
    return ProcessJiraRequestUseCase(agent, jira_provider, gitlab_provider)

@router.post("/jira-webhook", response_model=ArtifactResultModel, dependencies=[Depends(verify_api_key)])
def trigger_scaffold(
    payload: JiraWebhookDTO,
    usecase: ProcessJiraRequestUseCase = Depends(get_usecase)
):
    issue_key = payload.issue.key
    event_type = payload.webhook_event or "unknown"
    
    logger.info(f"Processing webhook for {issue_key}")
    
    mapper = JiraMapper()
    request = mapper.map_webhook_to_command(payload)
    
    try:
        code_result = usecase.execute(request)
        # For now, we return success with a placeholder URL, as we only generated code string.
        return ArtifactResultModel(
            run_id="sync-run",
            status=ArtifactRunStatusEnum.COMPLETED,
            issue_key=issue_key,
            mr_url="http://not-implemented-yet.com",
            branch_name="generated-code-in-logs"
        )
    except Exception as e:
        logger.error(f"Error processing jira request for {issue_key}: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": "Scaffolding mission failed",
                "detail": str(e),
                "issue_key": issue_key
            }
        )
