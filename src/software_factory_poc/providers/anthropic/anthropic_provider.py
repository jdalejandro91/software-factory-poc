from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from llm_bridge.core.entities.llm_request import LlmRequest
from llm_bridge.core.entities.llm_response import LlmResponse
from llm_bridge.core.exceptions.provider_error import ProviderError
from llm_bridge.core.value_objects.provider_name import ProviderName
from llm_bridge.providers.anthropic.anthropic_request_mapper import AnthropicRequestMapper
from llm_bridge.providers.anthropic.anthropic_response_mapper import AnthropicResponseMapper
from llm_bridge.providers.logging.correlation_id_context import CorrelationIdContext
from llm_bridge.providers.ports.llm_provider import LlmProvider
from llm_bridge.providers.retry.retry_policy import RetryPolicy


@dataclass(frozen=True, slots=True)
class AnthropicProvider(LlmProvider):
    client: Any
    retry: RetryPolicy
    request_mapper: AnthropicRequestMapper
    response_mapper: AnthropicResponseMapper
    correlation: CorrelationIdContext

    @property
    def name(self) -> ProviderName:
        return ProviderName.ANTHROPIC

    async def generate(self, request: LlmRequest) -> LlmResponse:
        cid = self.correlation.set(request.trace.correlation_id if request.trace else None)
        logging.getLogger(__name__).debug("Anthropic request model=%s cid=%s", request.model.name, cid)
        return await self.retry.run(lambda: self._call(request))

    async def _call(self, request: LlmRequest) -> LlmResponse:
        try:
            resp = await self.client.messages.create(**self.request_mapper.to_kwargs(request))
        except Exception as exc:
            raise self._map_error(exc)
        return self.response_mapper.to_domain(request.model.name, resp)

    def _map_error(self, exc: Exception) -> ProviderError:
        mod = self._anthropic_module()
        if mod is None:
            return ProviderError(provider=self.name, message=str(exc), retryable=True)
        return self._map_sdk_error(mod, exc)

    def _anthropic_module(self):
        try:
            import anthropic
        except ImportError:  # pragma: no cover
            return None
        return anthropic

    def _map_sdk_error(self, anthropic: Any, exc: Exception) -> ProviderError:
        if isinstance(exc, getattr(anthropic, "RateLimitError", ())):
            return ProviderError(provider=self.name, message=str(exc), retryable=True, status_code=429)
        if isinstance(exc, getattr(anthropic, "APIConnectionError", ())):
            return ProviderError(provider=self.name, message=str(exc), retryable=True)
        if isinstance(exc, getattr(anthropic, "AuthenticationError", ())):
            return ProviderError(provider=self.name, message=str(exc), retryable=False, status_code=401)
        if isinstance(exc, getattr(anthropic, "APIStatusError", ())):
            return self._map_status_error(exc)
        return ProviderError(provider=self.name, message=str(exc), retryable=False)

    def _map_status_error(self, exc: Any) -> ProviderError:
        code = getattr(exc, "status_code", None)
        retryable = bool(code in (429,) or (isinstance(code, int) and code >= 500))
        return ProviderError(provider=self.name, message=str(exc), retryable=retryable, status_code=code)
