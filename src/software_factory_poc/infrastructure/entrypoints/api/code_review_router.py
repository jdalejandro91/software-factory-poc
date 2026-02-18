import time
from functools import lru_cache

import structlog
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
from software_factory_poc.infrastructure.observability.metrics_service import (
    MISSION_DURATION_SECONDS,
    MISSIONS_INFLIGHT,
    MISSIONS_TOTAL,
)

logger = structlog.get_logger()
router = APIRouter()

_AGENT_LABEL = "code_reviewer"
_FLOW_MODE = "deterministic"


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

        background_tasks.add_task(_run_with_metrics, agent, task_entity)
        return {
            "status": "accepted",
            "message": "Code Review queued.",
            "issue_key": task_entity.key,
        }

    except Exception as e:
        logger.error(
            "Router error in code review trigger",
            processing_status="ERROR",
            error_type=type(e).__name__,
            error_details=str(e),
            error_retryable=False,
            context_endpoint="/webhooks/jira/code-review-trigger",
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": "error"},
        )


async def _run_with_metrics(agent: CodeReviewerAgent, mission: Mission) -> None:
    """Wrap agent.run with Prometheus metrics tracking."""
    MISSIONS_INFLIGHT.labels(agent=_AGENT_LABEL).inc()
    start = time.perf_counter()
    outcome = "success"
    try:
        await agent.run(mission)
    except Exception:
        outcome = "failure"
        raise
    finally:
        duration = time.perf_counter() - start
        MISSIONS_INFLIGHT.labels(agent=_AGENT_LABEL).dec()
        MISSION_DURATION_SECONDS.labels(agent=_AGENT_LABEL, flow_mode=_FLOW_MODE).observe(duration)
        MISSIONS_TOTAL.labels(agent=_AGENT_LABEL, flow_mode=_FLOW_MODE, outcome=outcome).inc()


async def _process_incoming_webhook(request: Request) -> Mission | JSONResponse:
    body_bytes = await request.body()
    try:
        payload = JiraWebhookDTO.model_validate_json(body_bytes)
        logger.info(
            "Received code review trigger",
            issue_key=payload.issue.key,
            context_endpoint="code-review-trigger",
        )
        return JiraPayloadMapper.to_domain(payload)
    except ValueError as e:
        logger.warning("Invalid request", error_type="ValueError", error_details=str(e))
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "ignored", "error": str(e)},
        )
