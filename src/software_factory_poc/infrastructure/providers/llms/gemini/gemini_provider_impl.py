from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from software_factory_poc.application.core.domain.agents.reasoner.llm_request import LlmRequest
from software_factory_poc.application.core.domain.agents.reasoner.llm_response import LlmResponse
from software_factory_poc.application.core.domain.agents.common.exceptions.provider_error import ProviderError
from software_factory_poc.application.core.domain.agents.common.config.llm_provider_type import LlmProviderType
from software_factory_poc.application.core.domain.agents.reasoner.ports.llm_provider import LlmProvider
from software_factory_poc.infrastructure.common.retry.retry_policy import RetryPolicy
from software_factory_poc.infrastructure.observability.logging.correlation_id_context import (
    CorrelationIdContext,
)
from software_factory_poc.infrastructure.providers.llms.gemini.mappers.gemini_request_mapper import (
    GeminiRequestMapper,
)
from software_factory_poc.infrastructure.providers.llms.gemini.mappers.gemini_response_mapper import (
    GeminiResponseMapper,
)


@dataclass(frozen=True, slots=True)
class GeminiProviderImpl(LlmProvider):
    client: Any
    retry: RetryPolicy
    request_mapper: GeminiRequestMapper
    response_mapper: GeminiResponseMapper
    correlation: CorrelationIdContext

    @property
    def name(self) -> LlmProviderType:
        return LlmProviderType.GEMINI

    async def generate(self, request: LlmRequest) -> LlmResponse:
        cid = self.correlation.set(request.trace.correlation_id if request.trace else None)
        logging.getLogger(__name__).debug("Gemini request model=%s cid=%s", request.model.name, cid)
        return await self.retry.run(lambda: self._call(request))

    async def _call(self, request: LlmRequest) -> LlmResponse:
        try:
            # 1. Prepare payload
            kwargs = self.request_mapper.to_kwargs(request)
            
            # 2. Debug Log
            prompt_content = kwargs.get("contents", "NO_CONTENT")
            prompt_content = kwargs.get("contents", "NO_CONTENT")
            print(f"\n🚀 [INFRA:LLM-SEND] Sending to {self.name.value.upper()}:\n"
                  f"--- BEGIN PROMPT ---\n{prompt_content}\n--- END PROMPT ---\n", flush=True)
            
            # 3. Execute
            resp = await self.client.models.generate_content(**kwargs)
        except Exception as exc:
            raise self._map_error(exc)
        return self.response_mapper.to_domain(request.model.name, resp)

    def _map_error(self, exc: Exception) -> ProviderError:
        status = getattr(exc, "code", None)
        code = status.value if hasattr(status, "value") else None
        retryable = self._is_retryable(exc, code)
        return ProviderError(provider=self.name, message=str(exc), retryable=retryable, status_code=code)

    def _is_retryable(self, exc: Exception, code: int | None) -> bool:
        if code in (429, 500, 502, 503, 504):
            return True
        name = type(exc).__name__.lower()
        return any(k in name for k in ("timeout", "deadline", "unavailable", "internal", "resourceexhausted"))
