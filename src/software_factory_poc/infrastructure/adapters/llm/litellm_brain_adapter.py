"""Implements BrainPort via ``litellm.acompletion`` with priority-based model fallback.

Includes full prompt visibility (redacted) and token usage tracking for SRE.
"""

import os
import time
from typing import Any, NoReturn

import litellm
import structlog
from pydantic import ValidationError

from software_factory_poc.core.application.ports import BrainPort, T
from software_factory_poc.core.application.tools.common.exceptions import ProviderError
from software_factory_poc.infrastructure.adapters.llm.config.llm_settings import LlmSettings
from software_factory_poc.infrastructure.adapters.llm.llm_observability_logger import (
    log_llm_request,
    log_llm_response,
)
from software_factory_poc.infrastructure.adapters.llm.llm_response_parser import (
    extract_tool_response,
    parse_structured_response,
)
from software_factory_poc.infrastructure.observability.tracing_setup import get_tracer

logger = structlog.get_logger()


class LiteLlmBrainAdapter(BrainPort):
    """Implements BrainPort via ``litellm.acompletion`` with priority-based model fallback."""

    def __init__(self, settings: LlmSettings) -> None:
        _inject_api_keys(settings)

    # ── Public contract ──

    async def generate_structured(
        self,
        prompt: str,
        schema: type[T],
        priority_models: list[str],
        system_prompt: str = "",
    ) -> T:
        messages = _build_messages(prompt, system_prompt)
        last_error: Exception | None = None
        for model_id in priority_models:
            try:
                return await self._structured_call(model_id, messages, schema)
            except (ProviderError, ValidationError):
                raise
            except Exception as exc:
                last_error = exc
                _log_model_failure(model_id, "generate_structured", exc)
        _raise_all_failed("generate_structured", priority_models, last_error)

    async def generate_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        priority_models: list[str],
    ) -> dict[str, Any]:
        last_error: Exception | None = None
        for model_id in priority_models:
            try:
                return await self._tools_call(model_id, messages, tools)
            except ProviderError:
                raise
            except Exception as exc:
                last_error = exc
                _log_model_failure(model_id, "generate_with_tools", exc)
        _raise_all_failed("generate_with_tools", priority_models, last_error)

    # ── Single-model call helpers ──

    async def _structured_call(
        self, model_id: str, messages: list[dict[str, str]], schema: type[T]
    ) -> T:
        response = await self._traced_completion(
            model_id, "generate_structured", messages=messages, response_format=schema
        )
        raw_content: str | None = response.choices[0].message.content
        return parse_structured_response(raw_content, schema, model_id)

    async def _tools_call(
        self,
        model_id: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> dict[str, Any]:
        response = await self._traced_completion(
            model_id, "generate_with_tools", messages=messages, tools=tools
        )
        return extract_tool_response(response)

    async def _traced_completion(self, model_id: str, method: str, **litellm_kwargs: Any) -> Any:
        """Execute a litellm.acompletion call with tracing, timing, and success logging."""
        log_llm_request(litellm_kwargs.get("messages", []), model_id, method)
        tracer = get_tracer()
        with tracer.start_as_current_span("llm.completion") as span:
            span.set_attribute("llm.model", model_id)
            span.set_attribute("llm.method", method)
            start = time.perf_counter()
            response = await litellm.acompletion(
                model=_normalize_model_id(model_id), **litellm_kwargs
            )
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            log_llm_response(response, model_id, duration_ms, method)
            return response


# ── Module-level pure functions ──


def _normalize_model_id(model_id: str) -> str:
    """Convert ``provider:model`` to ``provider/model`` for litellm routing."""
    return model_id.replace(":", "/", 1)


def _inject_api_keys(settings: LlmSettings) -> None:
    """Push non-null SecretStr keys into ``os.environ`` for litellm auto-detection."""
    mapping = {
        "OPENAI_API_KEY": settings.openai_api_key,
        "GEMINI_API_KEY": settings.gemini_api_key,
        "DEEPSEEK_API_KEY": settings.deepseek_api_key,
        "ANTHROPIC_API_KEY": settings.anthropic_api_key,
    }
    for env_var, secret in mapping.items():
        if secret is not None:
            os.environ[env_var] = secret.get_secret_value()


def _build_messages(user_prompt: str, system_prompt: str = "") -> list[dict[str, str]]:
    """Construct the messages array, optionally prepending a system message."""
    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})
    return messages


def _log_model_failure(model_id: str, method: str, exc: Exception) -> None:
    """Log a warning when a single model attempt fails during fallback iteration."""
    logger.warning(
        "Model failed",
        llm_model=model_id,
        method=method,
        error_type=type(exc).__name__,
        error_details=str(exc),
    )


def _raise_all_failed(
    method: str,
    priority_models: list[str],
    last_error: Exception | None,
) -> NoReturn:
    """Raise ``ProviderError`` after every model in the priority chain has failed."""
    raise ProviderError(
        provider="litellm",
        message=f"All {len(priority_models)} model(s) failed for {method}",
        retryable=True,
    ) from last_error
