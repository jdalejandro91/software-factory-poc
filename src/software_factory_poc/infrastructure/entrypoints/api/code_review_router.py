from functools import lru_cache

from fastapi import APIRouter, BackgroundTasks, Depends, Request, status
from fastapi.responses import JSONResponse

from software_factory_poc.core.application.agents.code_reviewer.code_reviewer_agent import (
    CodeReviewerAgent,
)
from software_factory_poc.core.domain.mission import Mission
from software_factory_poc.infrastructure.config.resolution.container import (
    McpConnectionManager,
    build_code_review_agent,
)
from software_factory_poc.infrastructure.entrypoints.api.dtos.jira_webhook_dto import JiraWebhookDTO
from software_factory_poc.infrastructure.entrypoints.api.mappers.jira_payload_mapper import (
    JiraPayloadMapper,
)
from software_factory_poc.infrastructure.entrypoints.api.security import validate_api_key
from software_factory_poc.infrastructure.observability.logger_factory_service import (
    LoggerFactoryService,
)

logger = LoggerFactoryService.build_logger(__name__)
router = APIRouter()


@lru_cache
def get_mcp_manager() -> McpConnectionManager:
    return McpConnectionManager()


async def get_agent(
    mcp_manager: McpConnectionManager = Depends(get_mcp_manager),
) -> CodeReviewerAgent:
    return await build_code_review_agent(mcp_manager)


@router.post(
    "/webhooks/jira/code-review-trigger",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(validate_api_key)],
)
async def trigger_code_review(
    request: Request,
    background_tasks: BackgroundTasks,
    agent: CodeReviewerAgent = Depends(get_agent),
):
    try:
        task_entity = await _process_incoming_webhook(request)
        if isinstance(task_entity, JSONResponse):
            return task_entity

        background_tasks.add_task(agent.run, task_entity)
        return {
            "status": "accepted",
            "message": "Code Review queued.",
            "issue_key": task_entity.key,
        }

    except Exception as e:
        logger.error(f"Router Error: {e}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": "error"},
        )


async def _process_incoming_webhook(request: Request) -> Mission | JSONResponse:
    body_bytes = await request.body()
    try:
        payload = JiraWebhookDTO.model_validate_json(body_bytes)
        logger.info(f"Received Code Review trigger for {payload.issue.key}")
        return JiraPayloadMapper.to_domain(payload)
    except ValueError as e:
        logger.warning(f"Invalid request: {e}")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "ignored", "error": str(e)},
        )
