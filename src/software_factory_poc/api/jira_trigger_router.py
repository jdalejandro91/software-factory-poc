from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, status

from software_factory_poc.config.settings_pydantic import Settings
from software_factory_poc.contracts.artifact_result_model import ArtifactResultModel
from software_factory_poc.contracts.jira_webhook_models import JiraWebhookModel
from software_factory_poc.contracts.scaffolding_contract_parser_service import (
    ScaffoldingContractParserService,
)
from software_factory_poc.integrations.gitlab.gitlab_client import GitLabClient
from software_factory_poc.integrations.gitlab.gitlab_payload_builder_service import (
    GitLabPayloadBuilderService,
)
from software_factory_poc.integrations.jira.jira_client import JiraClient
from software_factory_poc.integrations.jira.jira_issue_mapper_service import (
    JiraIssueMapperService,
)
from software_factory_poc.observability.logger_factory_service import build_logger
from software_factory_poc.orchestration.scaffold_orchestrator_service import (
    ScaffoldOrchestratorService,
)
from software_factory_poc.orchestration.step_runner_service import StepRunnerService
from software_factory_poc.policy.poc_policy_service import PocPolicyService
from software_factory_poc.store.idempotency_key_builder_service import (
    IdempotencyKeyBuilderService,
)
from software_factory_poc.store.idempotency_store_file_adapter import (
    IdempotencyStoreFileAdapter,
)
from software_factory_poc.store.run_result_store_file_adapter import (
    RunResultStoreFileAdapter,
)
from software_factory_poc.templates.template_file_loader_service import (
    TemplateFileLoaderService,
)
from software_factory_poc.templates.template_registry_service import (
    TemplateRegistryService,
)
from software_factory_poc.templates.template_renderer_service import (
    TemplateRendererService,
)

logger = build_logger(__name__)
router = APIRouter()

# Definimos que esperamos un header llamado "X-API-Key"
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

@lru_cache()
def get_settings() -> Settings:
    return Settings()

async def verify_api_key(
    api_key: str = Security(api_key_header), 
    settings: Settings = Depends(get_settings)
):
    if not api_key:
        raise HTTPException(status_code=403, detail="Missing X-API-Key header")
    if api_key != settings.jira_webhook_secret.get_secret_value():
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return api_key

def get_orchestrator(settings: Settings = Depends(get_settings)) -> ScaffoldOrchestratorService:
    # Instantiate all services
    
    # Observability
    step_runner = StepRunnerService()

    # Integrations
    jira_client = JiraClient(settings)
    jira_mapper = JiraIssueMapperService()
    
    payload_builder = GitLabPayloadBuilderService()
    gitlab_client = GitLabClient(settings, payload_builder)

    # Core Logic
    contract_parser = ScaffoldingContractParserService()
    template_registry = TemplateRegistryService(settings)
    template_loader = TemplateFileLoaderService()
    template_renderer = TemplateRendererService(template_registry, template_loader)
    policy_service = PocPolicyService(settings)

    # Persistence
    idempotency_builder = IdempotencyKeyBuilderService()
    idempotency_store = IdempotencyStoreFileAdapter(settings)
    run_result_store = RunResultStoreFileAdapter(settings)

    return ScaffoldOrchestratorService(
        settings=settings,
        step_runner=step_runner,
        jira_client=jira_client,
        jira_mapper=jira_mapper,
        contract_parser=contract_parser,
        template_registry=template_registry,
        template_loader=template_loader,
        template_renderer=template_renderer,
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
    except Exception as e:
        logger.exception(f"Unhandled error processing trigger for {issue_key}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during scaffolding execution."
        )
