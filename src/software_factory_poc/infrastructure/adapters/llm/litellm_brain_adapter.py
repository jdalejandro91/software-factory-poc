"""Implements BrainPort via ``litellm.acompletion`` with priority-based model fallback.

Includes full prompt visibility (redacted) and token usage tracking for SRE.
"""

import json
import os
import time
from typing import Any, NoReturn

import litellm
import structlog
from pydantic import ValidationError

from software_factory_poc.core.application.ports import BrainPort, T
from software_factory_poc.core.application.tools.common.exceptions import ProviderError
from software_factory_poc.infrastructure.adapters.llm.config.llm_settings import LlmSettings
from software_factory_poc.infrastructure.observability.metrics_service import (
    LLM_LATENCY_SECONDS,
    LLM_TOKENS_TOTAL,
)
from software_factory_poc.infrastructure.observability.redaction_service import redact_text
from software_factory_poc.infrastructure.observability.tracing_setup import get_tracer

logger = structlog.get_logger()


class LiteLlmBrainAdapter(BrainPort):
    """Implements BrainPort via ``litellm.acompletion`` with priority-based model fallback.

    API keys are extracted from the injected ``LlmSettings`` and pushed into
    ``os.environ`` so that litellm's internal provider auto-detection picks
    them up transparently.
    """

    def __init__(self, settings: LlmSettings) -> None:
        self._inject_api_keys(settings)

    # ── Public contract ──────────────────────────────────────────

    async def generate_structured(
        self,
        prompt: str,
        schema: type[T],
        priority_models: list[str],
        system_prompt: str = "",
    ) -> T:
        last_error: Exception | None = None
        tracer = get_tracer()

        for model_id in priority_models:
            try:
                messages = self._build_messages(prompt, system_prompt)
                self._log_outgoing_payload(messages, model_id, "generate_structured")

                with tracer.start_as_current_span("llm.completion") as span:
                    span.set_attribute("llm.model", model_id)
                    span.set_attribute("llm.method", "generate_structured")

                    start = time.perf_counter()
                    response = await litellm.acompletion(
                        model=self._normalize_model_id(model_id),
                        messages=messages,
                        response_format=schema,
                    )
                    duration_ms = round((time.perf_counter() - start) * 1000, 2)

                    self._log_inference_success(
                        response, model_id, duration_ms, "generate_structured"
                    )

                raw_content: str | None = response.choices[0].message.content
                return self._parse_structured_response(raw_content, schema, model_id)

            except (ProviderError, ValidationError):
                raise
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "Model failed",
                    llm_model=model_id,
                    method="generate_structured",
                    error_type=type(exc).__name__,
                    error_details=str(exc),
                )

        self._raise_all_failed("generate_structured", priority_models, last_error)

    async def generate_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        priority_models: list[str],
    ) -> dict[str, Any]:
        last_error: Exception | None = None
        tracer = get_tracer()

        for model_id in priority_models:
            try:
                self._log_outgoing_payload(messages, model_id, "generate_with_tools")

                with tracer.start_as_current_span("llm.completion") as span:
                    span.set_attribute("llm.model", model_id)
                    span.set_attribute("llm.method", "generate_with_tools")

                    start = time.perf_counter()
                    response = await litellm.acompletion(
                        model=self._normalize_model_id(model_id),
                        messages=messages,
                        tools=tools,
                    )
                    duration_ms = round((time.perf_counter() - start) * 1000, 2)

                    self._log_inference_success(
                        response, model_id, duration_ms, "generate_with_tools"
                    )

                return self._extract_tool_response(response)

            except ProviderError:
                raise
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "Model failed",
                    llm_model=model_id,
                    method="generate_with_tools",
                    error_type=type(exc).__name__,
                    error_details=str(exc),
                )

        self._raise_all_failed("generate_with_tools", priority_models, last_error)

    # ── Observability helpers ─────────────────────────────────────

    @staticmethod
    def _log_outgoing_payload(messages: list[dict[str, Any]], model_id: str, method: str) -> None:
        """Log the redacted prompt payload before sending to LLM."""
        raw_prompt = json.dumps(messages, ensure_ascii=False, default=str)
        redacted_prompt = redact_text(raw_prompt)
        logger.info(
            "Sending payload to LLM",
            prompt_text=redacted_prompt,
            llm_model=model_id,
            method=method,
            tags=["llm-prompt"],
        )

    @staticmethod
    def _log_inference_success(
        response: Any, model_id: str, duration_ms: float, method: str
    ) -> None:
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

    # ── Private helpers ──────────────────────────────────────────

    @staticmethod
    def _normalize_model_id(model_id: str) -> str:
        """Convert ``provider:model`` to ``provider/model`` for litellm routing."""
        return model_id.replace(":", "/", 1)

    @staticmethod
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

    @staticmethod
    def _parse_structured_response(
        raw_content: str | None,
        schema: type[T],
        model_id: str,
    ) -> T:
        """Deserialize JSON content and validate it against the Pydantic *schema*."""
        if not raw_content:
            raise ProviderError(
                provider=model_id,
                message="LLM returned empty content for structured request",
            )
        try:
            data = json.loads(raw_content)
        except json.JSONDecodeError as exc:
            raise ProviderError(
                provider=model_id,
                message=f"LLM returned invalid JSON: {exc}",
            ) from exc

        try:
            return schema.model_validate(data)
        except ValidationError as exc:
            raise ProviderError(
                provider=model_id,
                message=f"Structured response failed schema validation: {exc}",
            ) from exc

    @staticmethod
    def _extract_tool_response(response: Any) -> dict[str, Any]:
        """Normalize litellm's response into the dict shape expected by the Application layer."""
        message = response.choices[0].message
        result: dict[str, Any] = {"content": message.content or ""}

        if message.tool_calls:
            result["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": (
                            json.loads(tc.function.arguments)
                            if isinstance(tc.function.arguments, str)
                            else tc.function.arguments
                        ),
                    },
                }
                for tc in message.tool_calls
            ]
        return result

    @staticmethod
    def _build_messages(user_prompt: str, system_prompt: str = "") -> list[dict[str, str]]:
        """Construct the messages array, optionally prepending a system message."""
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})
        return messages

    @staticmethod
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
