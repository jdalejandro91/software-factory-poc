from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional

from software_factory_poc.application.core.agents.common.config.llm_provider_type import LlmProviderType
from software_factory_poc.application.core.agents.common.exceptions.provider_error import ProviderError
from software_factory_poc.application.core.agents.reasoner.llm_request import LlmRequest
from software_factory_poc.application.core.agents.reasoner.llm_response import LlmResponse
from software_factory_poc.application.core.agents.reasoner.ports.llm_provider import LlmProvider
from software_factory_poc.infrastructure.common.retry.retry_policy import RetryPolicy
from software_factory_poc.infrastructure.observability.logging.correlation_id_context import (
    CorrelationIdContext,
)
from software_factory_poc.infrastructure.providers.llms.gemini.clients.gemini_client_factory import (
    GeminiClientFactory,
)
from software_factory_poc.infrastructure.providers.llms.gemini.mappers.gemini_request_mapper import (
    GeminiRequestMapper,
)
from software_factory_poc.infrastructure.providers.llms.gemini.mappers.gemini_response_mapper import (
    GeminiResponseMapper,
)


@dataclass(frozen=True)
class GeminiProviderImpl(LlmProvider):
    client_factory: GeminiClientFactory
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
        
        # 1. Crear cliente efímero para esta solicitud
        client = self.client_factory.create()
        
        try:
            # 2. Pasar el cliente explícitamente a _call
            return await self.retry.run(lambda: self._call(client, request))
        finally:
            # 3. Cerrar cliente inmediatamente antes de que muera el Event Loop
            try:
                if hasattr(client, "close"):
                    client.close()
            except Exception as e:
                logging.getLogger(__name__).warning(f"Error closing ephemeral Gemini client: {e}")

    async def _call(self, client: Any, request: LlmRequest) -> LlmResponse:
        try:
            # 1. Prepare payload
            kwargs = self.request_mapper.to_kwargs(request)

            # 2. Debug Log
            prompt_content = kwargs.get("contents", "NO_CONTENT")
            logging.getLogger(__name__).debug(
                f"\n🚀 [INFRA:LLM-SEND] Sending to {self.name.value.upper()}:\n"
                f"--- BEGIN PROMPT ---\n{prompt_content}\n--- END PROMPT ---\n"
            )

            # 3. Execute ASYNC using .aio property
            resp = await client.aio.models.generate_content(**kwargs)

        except Exception as exc:
            raise self._map_error(exc)
        return self.response_mapper.to_domain(request.model.name, resp)

    def _map_error(self, exc: Exception) -> ProviderError:
        status = getattr(exc, "code", None)
        code = status.value if hasattr(status, "value") else None
        retryable = self._is_retryable(exc, code)
        return ProviderError(provider=self.name, message=str(exc), retryable=retryable, status_code=code)

    def _is_retryable(self, exc: Exception, code: Optional[int]) -> bool:
        if code in (429, 500, 502, 503, 504):
            return True
        name = type(exc).__name__.lower()
        return any(k in name for k in ("timeout", "deadline", "unavailable", "internal", "resourceexhausted"))