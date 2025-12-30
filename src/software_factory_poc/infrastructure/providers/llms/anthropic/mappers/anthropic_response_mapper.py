from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from software_factory_poc.application.core.entities.llm_response import LlmResponse
from software_factory_poc.application.core.value_objects.model_id import ModelId
from software_factory_poc.application.core.value_objects.provider_name import ProviderName
from software_factory_poc.application.core.value_objects.token_usage import TokenUsage


@dataclass(frozen=True, slots=True)
class AnthropicResponseMapper:
    def to_domain(self, model_name: str, response: Any) -> LlmResponse:
        content = self._text(response)
        usage = self._usage(response)
        payload = self._payload(response)
        return LlmResponse(model=ModelId(provider=ProviderName.ANTHROPIC, name=model_name), content=content, usage=usage, provider_payload=payload)

    def _text(self, response: Any) -> str:
        parts = [getattr(b, "text", "") for b in getattr(response, "content", []) or []]
        text = "".join(parts).strip()
        if not text:
            raise ValueError("Anthropic response did not contain text output")
        return text

    def _usage(self, response: Any) -> TokenUsage | None:
        u = getattr(response, "usage", None)
        if u is None:
            return None
        return TokenUsage(input_tokens=getattr(u, "input_tokens", None), output_tokens=getattr(u, "output_tokens", None))

    def _payload(self, response: Any) -> Mapping[str, Any]:
        return {"id": getattr(response, "id", None), "model": getattr(response, "model", None), "stop_reason": getattr(response, "stop_reason", None)}
