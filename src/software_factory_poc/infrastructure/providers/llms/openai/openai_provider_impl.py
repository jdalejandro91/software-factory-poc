from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from software_factory_poc.application.core.domain.entities.llm.llm_request import LlmRequest
from software_factory_poc.application.core.domain.entities.llm.llm_response import LlmResponse
from software_factory_poc.application.core.domain.exceptions.provider_error import ProviderError
from software_factory_poc.application.core.domain.configuration.llm_provider_type import LlmProviderType
from software_factory_poc.application.core.ports.llms.llm_provider import LlmProvider
from software_factory_poc.infrastructure.common.retry.retry_policy import RetryPolicy
from software_factory_poc.infrastructure.observability.logging.correlation_id_context import (
    CorrelationIdContext,
)
from software_factory_poc.infrastructure.providers.llms.openai.mappers.openai_request_mapper import (
    OpenAiRequestMapper,
)
from software_factory_poc.infrastructure.providers.llms.openai.mappers.openai_response_mapper import (
    OpenAiResponseMapper,
)


@dataclass(frozen=True, slots=True)
class OpenAiProvider(LlmProvider):
    client: Any
    retry: RetryPolicy
    request_mapper: OpenAiRequestMapper
    response_mapper: OpenAiResponseMapper
    correlation: CorrelationIdContext

    @property
    def name(self) -> LlmProviderType:
        return LlmProviderType.OPENAI

    async def generate(self, request: LlmRequest) -> LlmResponse:
        cid = self.correlation.set(request.trace.correlation_id if request.trace else None)
        logging.getLogger(__name__).debug("OpenAI request model=%s cid=%s", request.model.name, cid)
        return await self.retry.run(lambda: self._call(request))

    async def _call(self, request: LlmRequest) -> LlmResponse:
        try:
            # 1. Obtener argumentos base del mapper
            kwargs = self.request_mapper.to_kwargs(request)
            
            # 2. Inyectar 'response_format' si el config lo pide (JSON Mode nativo)
            # Nota: Esto es soportado por gpt-4-turbo y gpt-3.5-turbo-1106+
            if request.generation.json_mode:
                kwargs["response_format"] = {"type": "json_object"}
            
            # 3. Debug Logging for Audit
            import json
            msgs = kwargs.get("messages", [])
            debug_payload = json.dumps(msgs, indent=2, ensure_ascii=False)
            logging.getLogger(__name__).info(
                f"\n🚀 [OPENAI PROMPT SENDING] ({request.model.name}):\n{debug_payload}\n"
            )

            # 4. Llamada Oficial SDK v1
            # logging.debug(f"OpenAI Payload: {kwargs}") # Descomentar para debug local
            resp = await self.client.chat.completions.create(**kwargs)
            
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
