from functools import lru_cache
from typing import Union

from fastapi import APIRouter, BackgroundTasks, Depends, status, Request
from fastapi.responses import JSONResponse

from software_factory_poc.domain.entities.task import Task
from software_factory_poc.application.usecases.scaffolding.create_scaffolding_usecase import (
    CreateScaffoldingUseCase,
)
from software_factory_poc.infrastructure.configuration.app_config import AppConfig
from software_factory_poc.infrastructure.configuration.main_settings import Settings
from software_factory_poc.infrastructure.entrypoints.api.dtos.jira_webhook_dto import JiraWebhookDTO
from software_factory_poc.infrastructure.entrypoints.api.mappers.jira_payload_mapper import JiraPayloadMapper
from software_factory_poc.infrastructure.entrypoints.api.security import validate_api_key
from software_factory_poc.infrastructure.observability.logger_factory_service import LoggerFactoryService
from software_factory_poc.infrastructure.resolution.provider_resolver import ProviderResolver

logger = LoggerFactoryService.build_logger(__name__)
router = APIRouter()

@lru_cache
def get_settings() -> Settings:
    return Settings()

def get_usecase(settings: Settings = Depends(get_settings)) -> CreateScaffoldingUseCase:
    from software_factory_poc.infrastructure.configuration.scaffolding_config_loader import ScaffoldingConfigLoader
    scaffolding_config = ScaffoldingConfigLoader.load_config()
    
    app_config = AppConfig()
    resolver = ProviderResolver(scaffolding_config, app_config=app_config)
    
    return CreateScaffoldingUseCase(
        config=scaffolding_config,
        resolver=resolver
    )

@router.post("/webhooks/jira/scaffolding-trigger", status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(validate_api_key)])
async def trigger_scaffold(
    request: Request,
    background_tasks: BackgroundTasks,
    usecase: CreateScaffoldingUseCase = Depends(get_usecase)
):
    try:
        task_entity = await _process_incoming_webhook(request)
        
        if isinstance(task_entity, JSONResponse):
            return task_entity
            
        # Fire and Forget
        background_tasks.add_task(usecase.execute, task_entity)
        
        return {
            "status": "accepted",
            "message": "Scaffolding request queued.",
            "issue_key": task_entity.key
        }
    except Exception as e:
         # Generic catch-all to prevent 500s from leaking if _process fails unexpectedly
         logger.error(f"Router Error: {e}")
         return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"status": "error", "message": "Internal processing error."})

async def _process_incoming_webhook(request: Request) -> Union[Task, JSONResponse]:
    """Helper to parse, validate and map webhook."""
    body_bytes = await request.body()
    try:
        logger.info(f"Incoming Jira Payload (Raw): {body_bytes.decode('utf-8')}")
        payload = JiraWebhookDTO.model_validate_json(body_bytes)
        
        issue_key = payload.issue.key
        logger.info(f"Processing webhook for {issue_key}")
        
        return JiraPayloadMapper.to_domain(payload)
        
    except ValueError as e:
        logger.warning(f"Skipping webhook: {e}")
        return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "ignored", "message": str(e)})
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        # If parsing fails entirely (malformed JSON), return 200 to satisfy Jira
        return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "error", "message": str(e)})
