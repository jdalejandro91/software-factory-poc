from functools import lru_cache

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Security, status, Request
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from software_factory_poc.infrastructure.observability.logger_factory_service import LoggerFactoryService 

from software_factory_poc.application.core.agents.scaffolding.value_objects.scaffolding_order import (
    ScaffoldingOrder,
)
from software_factory_poc.application.usecases.scaffolding.create_scaffolding_usecase import (
    CreateScaffoldingUseCase,
)
from software_factory_poc.infrastructure.configuration.main_settings import Settings
from software_factory_poc.infrastructure.configuration.app_config import AppConfig
from software_factory_poc.infrastructure.entrypoints.api.dtos.jira_webhook_dto import JiraWebhookDTO
# from software_factory_poc.infrastructure.entrypoints.api.mappers.jira_mapper import JiraMapper # Legacy mapper removed/deprecated
from software_factory_poc.infrastructure.entrypoints.api.mappers.jira_payload_mapper import JiraPayloadMapper
from software_factory_poc.infrastructure.resolution.provider_resolver import ProviderResolver
from software_factory_poc.infrastructure.entrypoints.api.security import validate_api_key


logger = LoggerFactoryService.build_logger(__name__)
router = APIRouter()

@lru_cache
def get_settings() -> Settings:
    return Settings()

def get_usecase(settings: Settings = Depends(get_settings)) -> CreateScaffoldingUseCase:
    from software_factory_poc.infrastructure.configuration.scaffolding_config_loader import ScaffoldingConfigLoader
    scaffolding_config = ScaffoldingConfigLoader.load_config()
    
    # 2. Infra Resolver (The "Switch")
    # Instantiate AppConfig (Centralized Configuration)
    # Ideally should be done once via Depends(get_app_config) but for now local instantiation works 
    # as it reads env vars efficiently (Pydantic caches/lazy loads if configured, or just fast enough).
    app_config = AppConfig()
    
    # Use the injected settings which contains environment variables loaded once
    resolver = ProviderResolver(scaffolding_config, app_config=app_config)
    
    # 3. Use Case
    return CreateScaffoldingUseCase(
        config=scaffolding_config,
        resolver=resolver
    )

@router.post("/jira-webhook", status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(validate_api_key)])
async def trigger_scaffold(
    request: Request,
    background_tasks: BackgroundTasks,
    usecase: CreateScaffoldingUseCase = Depends(get_usecase)
):
    # Extract Logic (< 12 lines goal for main logic)
    jira_request = await _process_incoming_webhook(request)
    
    if isinstance(jira_request, JSONResponse):
        return jira_request
        
    # Fire and Forget
    background_tasks.add_task(usecase.execute, jira_request)
    
    return {
        "status": "accepted",
        "message": "Scaffolding request queued.",
        "issue_key": jira_request.issue_key
    }

async def _process_incoming_webhook(request: Request) -> ScaffoldingOrder | JSONResponse:
    """Helper to parse, validate and map webhook."""
    body_bytes = await request.body()
    try:
        logger.info(f"Incoming Jira Payload (Raw): {body_bytes.decode('utf-8')}")
        payload = JiraWebhookDTO.model_validate_json(body_bytes)
        
        issue_key = payload.issue.key
        logger.info(f"Processing webhook for {issue_key}")
        
        return JiraPayloadMapper.map_to_request(payload)
        
    except ValueError as e:
        logger.warning(f"Skipping webhook: {e}")
        return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "ignored", "message": str(e)})
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        # If parsing fails entirely (malformed JSON), return 200 to satisfy Jira
        return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "error", "message": str(e)})
