from functools import lru_cache
from typing import Union

from fastapi import APIRouter, BackgroundTasks, Depends, status, Request
from fastapi.responses import JSONResponse

from software_factory_poc.application.core.domain.entities.task import Task
from software_factory_poc.application.usecases.code_review.perform_code_review_usecase import (
    PerformCodeReviewUseCase,
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


def get_code_review_usecase(settings: Settings = Depends(get_settings)) -> PerformCodeReviewUseCase:
    from software_factory_poc.infrastructure.configuration.scaffolding_config_loader import ScaffoldingConfigLoader
    
    # We reuse ScaffoldingConfigLoader for now as the base config, 
    # but ProviderResolver creates a specific CodeReviewerAgentConfig internally.
    scaffolding_config = ScaffoldingConfigLoader.load_config()
    app_config = AppConfig()
    
    resolver = ProviderResolver(scaffolding_config, app_config=app_config)
    return resolver.create_perform_code_review_usecase()


@router.post("/webhooks/jira/code-review-trigger", status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(validate_api_key)])
async def trigger_code_review(
    request: Request,
    background_tasks: BackgroundTasks,
    usecase: PerformCodeReviewUseCase = Depends(get_code_review_usecase)
):
    try:
        task_entity = await _process_incoming_webhook(request)
        
        if isinstance(task_entity, JSONResponse):
            return task_entity
            
        # 3. Execute Async
        background_tasks.add_task(usecase.execute, task_entity)
        
        return {
            "status": "accepted", 
            "message": "Code Review request queued.",
            "issue_key": task_entity.key
        }
        
    except Exception as e:
        logger.error(f"Router Error: {e}", exc_info=True)
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"status": "error", "error": "Internal processing error."})


async def _process_incoming_webhook(request: Request) -> Union[Task, JSONResponse]:
    """Helper to parse, validate and map webhook."""
    body_bytes = await request.body()
    try:
        # 1. Parse DTO
        payload = JiraWebhookDTO.model_validate_json(body_bytes)
        logger.info(f"Received Code Review trigger for {payload.issue.key}")
        
        # 2. Map to Domain Task (Uses new generic mapper)
        return JiraPayloadMapper.to_domain(payload)
        
    except ValueError as e:
        logger.warning(f"Invalid request: {e}")
        # Return 200 to Jira to avoid retries on bad data
        return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "ignored", "error": str(e)})
