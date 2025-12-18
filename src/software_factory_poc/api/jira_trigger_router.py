from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from software_factory_poc.config.settings_pydantic import Settings
from software_factory_poc.contracts.artifact_result_model import ArtifactResultModel
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


class JiraTriggerRequest(BaseModel):
    issue_key: str


@lru_cache()
def get_settings() -> Settings:
    return Settings()


def get_orchestrator(settings: Settings = Depends(get_settings)) -> ScaffoldOrchestratorService:
    # Instantiate all services
    # In a real app, use a proper DI framework or structured providers
    
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


@router.post("/jira/scaffold-trigger", response_model=ArtifactResultModel)
def trigger_scaffold(
    request: JiraTriggerRequest,
    orchestrator: ScaffoldOrchestratorService = Depends(get_orchestrator)
):
    logger.info(f"Received trigger for issue: {request.issue_key}")
    try:
        result = orchestrator.execute(request.issue_key)
        return result
    except Exception as e:
        logger.exception(f"Unhandled error processing trigger for {request.issue_key}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during scaffolding execution."
        )
