from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, Security, status
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
from software_factory_poc.contracts.artifact_result_model import ArtifactResultModel
from software_factory_poc.contracts.scaffolding_contract_parser_service import (
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
from software_factory_poc.infrastructure.providers.tools.jira.dtos.jira_webhook_models import (
    JiraWebhookModel,
)
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
from software_factory_poc.observability.logger_factory_service import build_logger
from software_factory_poc.orchestration.step_runner_service import StepRunnerService
from software_factory_poc.policy.poc_policy_service import PocPolicyService
from software_factory_poc.providers.facade.llm_bridge import LlmBridge

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

@router.post("/jira-webhook", response_model=ArtifactResultModel, dependencies=[Depends(verify_api_key)])
def trigger_scaffold(
    payload: JiraWebhookModel,
    orchestrator: ScaffoldOrchestratorService = Depends(get_orchestrator)
):
    issue_key = payload.issue.key
    event_type = payload.webhookEvent or "unknown"
    user_display = payload.user.displayName if payload.user else "unknown"

    logger.info(
        f"Recibido evento '{event_type}' por usuario '{user_display}' para issue '{issue_key}'"
    )

    try:
        result = orchestrator.execute(issue_key, payload)
        return result
    except Exception:
        logger.exception(f"Unhandled error processing trigger for {issue_key}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during scaffolding execution."
        )
