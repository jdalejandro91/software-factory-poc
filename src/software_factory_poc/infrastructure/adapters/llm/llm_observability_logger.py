"""Pure functions for logging LLM request/response payloads with redaction and Prometheus metrics."""

import json
from typing import Any

import structlog

from software_factory_poc.infrastructure.observability.metrics_service import (
    LLM_LATENCY_SECONDS,
    LLM_TOKENS_TOTAL,
)
from software_factory_poc.infrastructure.observability.redaction_service import redact_text

logger = structlog.get_logger()

_MAX_LOG_PROMPT_LENGTH = 10_000


def log_llm_request(messages: list[dict[str, Any]], model_id: str, method: str) -> None:
    """Log the redacted prompt payload before sending to LLM."""
    raw_prompt = json.dumps(messages, ensure_ascii=False, default=str)
    redacted_prompt = redact_text(raw_prompt)
    if len(redacted_prompt) > _MAX_LOG_PROMPT_LENGTH:
        redacted_prompt = redacted_prompt[:_MAX_LOG_PROMPT_LENGTH] + "... [TRUNCATED]"
    logger.info(
        "Sending payload to LLM",
        prompt_text=redacted_prompt,
        llm_model=model_id,
        method=method,
        tags=["llm-prompt"],
    )


def log_llm_response(response: Any, model_id: str, duration_ms: float, method: str) -> None:
    """Log successful inference with token usage and duration, and record Prometheus metrics."""
    usage = getattr(response, "usage", None)
    tokens_in = getattr(usage, "prompt_tokens", 0) if usage else 0
    tokens_out = getattr(usage, "completion_tokens", 0) if usage else 0

    LLM_TOKENS_TOTAL.labels(model=model_id, type="prompt").inc(tokens_in)
    LLM_TOKENS_TOTAL.labels(model=model_id, type="completion").inc(tokens_out)
    LLM_LATENCY_SECONDS.labels(model=model_id).observe(duration_ms / 1000)

    logger.info(
        "LLM inference completed",
        llm_model=model_id,
        method=method,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        processing_status="SUCCESS",
        processing_duration_ms=duration_ms,
        tags=["llm-response"],
    )
