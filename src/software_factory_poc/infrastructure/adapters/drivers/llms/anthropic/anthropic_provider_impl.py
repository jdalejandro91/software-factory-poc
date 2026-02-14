from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from software_factory_poc.application.ports.drivers.common.config.llm_provider_type import LlmProviderType
from software_factory_poc.application.ports.drivers.common.exceptions import ProviderError
from software_factory_poc.application.ports.drivers.reasoner.llm_request import LlmRequest
from software_factory_poc.application.ports.drivers.reasoner import LlmResponse
from software_factory_poc.application.ports.drivers.reasoner.ports.llm_provider import LlmProvider
from software_factory_poc.infrastructure.common.retry.retry_policy import RetryPolicy
from software_factory_poc.infrastructure.observability.logging.correlation_id_context import (
    CorrelationIdContext,
)
from software_factory_poc.infrastructure.adapters.drivers.llms.anthropic.mappers.anthropic_request_mapper import (
    AnthropicRequestMapper,
)
from software_factory_poc.infrastructure.adapters.drivers.llms.anthropic.mappers.anthropic_response_mapper import (
    AnthropicResponseMapper,
)


@dataclass(frozen=True)
class AnthropicProviderImpl(LlmProvider):
    client: Any
    retry: RetryPolicy
    request_mapper: AnthropicRequestMapper
    response_mapper: AnthropicResponseMapper
    correlation: CorrelationIdContext

    @property
    def name(self) -> LlmProviderType:
        return LlmProviderType.ANTHROPIC

    async def generate(self, request: LlmRequest) -> LlmResponse:
        cid = self.correlation.set(request.trace.correlation_id if request.trace else None)
        logging.getLogger(__name__).debug("Anthropic request model=%s cid=%s", request.model.name, cid)
        return await self.retry.run(lambda: self._call(request))

    async def _call(self, request: LlmRequest) -> LlmResponse:
        try:
            kwargs = self.request_mapper.to_kwargs(request)
            
            # --- LOG DE VERDAD ÚLTIMA ---
            import json
            try:
                msgs = kwargs.get("messages", [])
                system = kwargs.get("system", "")
                debug_payload = f"System: {system}\nMessages:\n{json.dumps(msgs, indent=2, ensure_ascii=False)}"
            except:
                debug_payload = str(kwargs)

            print(f"\n🚀 [INFRA:LLM-SEND] Sending to {self.name.value.upper()}:\n"
                  f"{debug_payload}\n"
                  f"Config: {kwargs.get('max_tokens')}, {kwargs.get('temperature')}\n", flush=True)
            # ---------------------------

            resp = await self.client.messages.create(**kwargs)
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
