import time
from typing import Any

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, Request, status
from fastapi.responses import JSONResponse
from structlog.contextvars import bind_contextvars, clear_contextvars, get_contextvars

from software_factory_poc.core.application.agents.scaffolder.scaffolder_agent import ScaffolderAgent
from software_factory_poc.core.domain.mission import Mission
from software_factory_poc.infrastructure.config.resolution.container import (
    build_scaffolding_agent,
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
from software_factory_poc.infrastructure.observability.redaction_service import redact_text
from software_factory_poc.infrastructure.observability.tracing_setup import get_tracer

logger = structlog.get_logger()
router = APIRouter()

_AGENT_LABEL = "scaffolder"
_FLOW_MODE = "deterministic"


async def get_agent() -> ScaffolderAgent:
    """Build a fresh agent with isolated MCP drivers for each request."""
    return await build_scaffolding_agent()


@router.post(
    "/webhooks/jira/scaffolding-trigger",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(validate_api_key)],
    response_model=None,
)
async def trigger_scaffold(
    request: Request,
    background_tasks: BackgroundTasks,
    agent: ScaffolderAgent = Depends(get_agent),
) -> dict[str, str] | JSONResponse:
    try:
        task_entity = await _process_incoming_webhook(request)

        if isinstance(task_entity, JSONResponse):
            return task_entity

        ctx_snapshot = get_contextvars()
        background_tasks.add_task(_run_with_metrics, agent, task_entity, ctx_snapshot)

        return {
            "status": "accepted",
            "message": "Scaffolding request queued.",
            "issue_key": task_entity.key,
        }
    except Exception as exc:
        logger.error(
            "Router error in scaffolding trigger",
            processing_status="ERROR",
            error_type=type(exc).__name__,
            error_details=str(exc),
            error_retryable=False,
            context_endpoint="/webhooks/jira/scaffolding-trigger",
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": "error", "message": "Internal processing error."},
        )


async def _run_with_metrics(
    agent: ScaffolderAgent, mission: Mission, ctx_snapshot: dict[str, Any]
) -> None:
    """Wrap agent.run with Prometheus metrics tracking and context propagation."""
    _restore_context(ctx_snapshot)
    MISSIONS_INFLIGHT.labels(agent=_AGENT_LABEL).inc()
    start = time.perf_counter()
    outcome = "success"
    try:
        with get_tracer().start_as_current_span("workflow.scaffold"):
            await agent.run(mission)
    except Exception:
        outcome = "failure"
        raise
    finally:
        _record_mission_outcome(start, outcome)


def _restore_context(ctx_snapshot: dict[str, Any]) -> None:
    """Re-bind structlog contextvars from a snapshot captured in the request scope."""
    clear_contextvars()
    bind_contextvars(**ctx_snapshot)


def _record_mission_outcome(start: float, outcome: str) -> None:
    """Record Prometheus metrics for a completed mission run."""
    duration = time.perf_counter() - start
    MISSIONS_INFLIGHT.labels(agent=_AGENT_LABEL).dec()
    MISSION_DURATION_SECONDS.labels(agent=_AGENT_LABEL, flow_mode=_FLOW_MODE).observe(duration)
    MISSIONS_TOTAL.labels(agent=_AGENT_LABEL, flow_mode=_FLOW_MODE, outcome=outcome).inc()


async def _process_incoming_webhook(request: Request) -> Mission | JSONResponse:
    """Parse, validate and map a Jira webhook into a domain Mission."""
    body_bytes = await request.body()
    _log_raw_webhook(body_bytes, "scaffolding-trigger")
    try:
        payload = JiraWebhookDTO.model_validate_json(body_bytes)
        logger.info("Processing webhook", issue_key=payload.issue.key)
        return JiraPayloadMapper.to_domain(payload)
    except ValueError as exc:
        logger.warning("Skipping webhook", error_type="ValueError", error_details=str(exc))
        return JSONResponse(
            status_code=status.HTTP_200_OK, content={"status": "ignored", "message": str(exc)}
        )
    except Exception as exc:
        logger.error(
            "Error processing webhook",
            processing_status="ERROR",
            error_type=type(exc).__name__,
            error_details=str(exc),
            error_retryable=False,
        )
        return JSONResponse(
            status_code=status.HTTP_200_OK, content={"status": "error", "message": str(exc)}
        )


def _log_raw_webhook(body_bytes: bytes, endpoint: str) -> None:
    """Log the raw webhook payload (redacted) for observability."""
    raw_payload = body_bytes.decode("utf-8", errors="replace")
    logger.info(
        "Raw Jira webhook payload received",
        raw_payload=redact_text(raw_payload),
        context_endpoint=endpoint,
        tags=["webhook-raw"],
    )
