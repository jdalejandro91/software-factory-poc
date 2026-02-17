from functools import lru_cache

from fastapi import APIRouter, BackgroundTasks, Depends, Request, status
from fastapi.responses import JSONResponse

from software_factory_poc.core.application.agents.scaffolder.scaffolder_agent import ScaffolderAgent
from software_factory_poc.core.domain.mission.entities import Mission
from software_factory_poc.infrastructure.configuration.resolution.container import (
    McpConnectionManager,
    build_scaffolding_agent,
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
) -> ScaffolderAgent:
    return await build_scaffolding_agent(mcp_manager)


@router.post(
    "/webhooks/jira/scaffolding-trigger",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(validate_api_key)],
)
async def trigger_scaffold(
    request: Request,
    background_tasks: BackgroundTasks,
    agent: ScaffolderAgent = Depends(get_agent),
):
    try:
        task_entity = await _process_incoming_webhook(request)

        if isinstance(task_entity, JSONResponse):
            return task_entity

        background_tasks.add_task(agent.execute_flow, task_entity)

        return {
            "status": "accepted",
            "message": "Scaffolding request queued.",
            "issue_key": task_entity.key,
        }
    except Exception as e:
        logger.error(f"Router Error: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": "error", "message": "Internal processing error."},
        )


async def _process_incoming_webhook(request: Request) -> Mission | JSONResponse:
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
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "ignored", "message": str(e)},
        )
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "error", "message": str(e)},
        )
