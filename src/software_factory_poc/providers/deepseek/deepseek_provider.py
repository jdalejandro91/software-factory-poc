from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from llm_bridge.core.entities.llm_request import LlmRequest
from llm_bridge.core.entities.llm_response import LlmResponse
from llm_bridge.core.exceptions.provider_error import ProviderError
from llm_bridge.core.value_objects.provider_name import ProviderName
from llm_bridge.providers.deepseek.deepseek_request_mapper import DeepSeekRequestMapper
from llm_bridge.providers.deepseek.deepseek_response_mapper import DeepSeekResponseMapper
from llm_bridge.providers.logging.correlation_id_context import CorrelationIdContext
from llm_bridge.providers.ports.llm_provider import LlmProvider
from llm_bridge.providers.retry.retry_policy import RetryPolicy


@dataclass(frozen=True, slots=True)
class DeepSeekProvider(LlmProvider):
    client: Any
    retry: RetryPolicy
    request_mapper: DeepSeekRequestMapper
    response_mapper: DeepSeekResponseMapper
    correlation: CorrelationIdContext

    @property
    def name(self) -> ProviderName:
        return ProviderName.DEEPSEEK

    async def generate(self, request: LlmRequest) -> LlmResponse:
        cid = self.correlation.set(request.trace.correlation_id if request.trace else None)
        logging.getLogger(__name__).debug("DeepSeek request model=%s cid=%s", request.model.name, cid)
        return await self.retry.run(lambda: self._call(request))

    async def _call(self, request: LlmRequest) -> LlmResponse:
        try:
            resp = await self.client.chat.completions.create(**self.request_mapper.to_kwargs(request))
        except Exception as exc:
            raise self._map_error(exc)
        return self.response_mapper.to_domain(request.model.name, resp)

    def _map_error(self, exc: Exception) -> ProviderError:
        mod = self._openai_module()
        if mod is None:
            return ProviderError(provider=self.name, message=str(exc), retryable=True)
        return self._map_openai_error(mod, exc)

    def _openai_module(self):
        try:
            import openai
        except ImportError:  # pragma: no cover
            return None
        return openai

    def _map_openai_error(self, openai: Any, exc: Exception) -> ProviderError:
        if isinstance(exc, openai.RateLimitError):
            return ProviderError(provider=self.name, message=str(exc), retryable=True, status_code=429)
        if isinstance(exc, openai.APIConnectionError):
            return ProviderError(provider=self.name, message=str(exc), retryable=True)
        if isinstance(exc, openai.AuthenticationError):
            return ProviderError(provider=self.name, message=str(exc), retryable=False, status_code=401)
        if isinstance(exc, openai.APIStatusError):
            return self._map_status_error(exc)
        return ProviderError(provider=self.name, message=str(exc), retryable=False)

    def _map_status_error(self, exc: Any) -> ProviderError:
        code = getattr(exc, "status_code", None)
        retryable = bool(code in (429,) or (isinstance(code, int) and code >= 500))
        return ProviderError(provider=self.name, message=str(exc), retryable=retryable, status_code=code)
