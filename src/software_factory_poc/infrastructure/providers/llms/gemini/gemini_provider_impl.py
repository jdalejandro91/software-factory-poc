from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from software_factory_poc.application.core.entities.llm_request import LlmRequest
from software_factory_poc.application.core.entities.llm_response import LlmResponse
from software_factory_poc.application.core.exceptions.provider_error import ProviderError
from software_factory_poc.application.core.value_objects.provider_name import ProviderName
from software_factory_poc.application.ports.llms.llm_provider import LlmProvider
from software_factory_poc.infrastructure.providers.llms.gemini.mappers.gemini_request_mapper import (
    GeminiRequestMapper,
)
from software_factory_poc.infrastructure.providers.llms.gemini.mappers.gemini_response_mapper import (
    GeminiResponseMapper,
)
from software_factory_poc.infrastructure.observability.logging.correlation_id_context import CorrelationIdContext
from software_factory_poc.infrastructure.common.retry.retry_policy import RetryPolicy


@dataclass(frozen=True, slots=True)
class GeminiProvider(LlmProvider):
    client: Any
    retry: RetryPolicy
    request_mapper: GeminiRequestMapper
    response_mapper: GeminiResponseMapper
    correlation: CorrelationIdContext

    @property
    def name(self) -> ProviderName:
        return ProviderName.GEMINI

    async def generate(self, request: LlmRequest) -> LlmResponse:
        cid = self.correlation.set(request.trace.correlation_id if request.trace else None)
        logging.getLogger(__name__).debug("Gemini request model=%s cid=%s", request.model.name, cid)
        return await self.retry.run(lambda: self._call(request))

    async def _call(self, request: LlmRequest) -> LlmResponse:
        try:
            resp = await self.client.models.generate_content(**self.request_mapper.to_kwargs(request))
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
