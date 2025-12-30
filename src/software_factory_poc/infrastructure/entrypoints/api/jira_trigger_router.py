from functools import lru_cache

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Security, status
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from software_factory_poc.infrastructure.observability.logger_factory_service import LoggerFactoryService 

from software_factory_poc.application.core.domain.entities.scaffolding.scaffolding_request import (
    ScaffoldingRequest,
)
from software_factory_poc.application.usecases.scaffolding.create_scaffolding_usecase import (
    CreateScaffoldingUseCase,
)
from software_factory_poc.infrastructure.configuration.main_settings import Settings
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
    from software_factory_poc.infrastructure.configuration.tool_settings import ToolSettings
    tool_settings = ToolSettings()
    
    resolver = ProviderResolver(scaffolding_config, tool_settings)
    
    # 3. Use Case
    return CreateScaffoldingUseCase(
        config=scaffolding_config,
        resolver=resolver
    )

@router.post("/jira-webhook", status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(validate_api_key)])
def trigger_scaffold(
    payload: JiraWebhookDTO,
    background_tasks: BackgroundTasks,
    usecase: CreateScaffoldingUseCase = Depends(get_usecase)
):
    issue_key = payload.issue.key
    logger.info(f"Webhook received for {issue_key}. Processing with JiraPayloadMapper.")
    
    try:
        # Use new Mapper with YAML extraction
        request = JiraPayloadMapper.map_to_request(payload)
    except ValueError as e:
        logger.warning(f"Skipping webhook for {issue_key}: {e}")
        # We return 200 OK to Jira so it doesn't retry events that are just invalid/ignored
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "ignored",
                "message": str(e),
                "issue_key": issue_key
            }
        )
    except Exception as e:
        logger.error(f"Unexpected error mapping payload for {issue_key}: {e}")
        raise HTTPException(status_code=500, detail="Internal processing error")

    # Fire and Forget
    background_tasks.add_task(usecase.execute, request)
    
    return {
        "status": "accepted",
        "message": "Scaffolding request queued.",
        "issue_key": issue_key
    }
