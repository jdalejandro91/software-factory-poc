from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from llm_bridge.core.entities.llm_response import LlmResponse
from llm_bridge.core.value_objects.model_id import ModelId
from llm_bridge.core.value_objects.provider_name import ProviderName
from llm_bridge.core.value_objects.token_usage import TokenUsage


@dataclass(frozen=True, slots=True)
class OpenAiResponseMapper:
    def to_domain(self, model_name: str, response: Any) -> LlmResponse:
        content = self._output_text(response)
        usage = self._usage(response)
        payload = self._payload(response)
        return LlmResponse(model=ModelId(provider=ProviderName.OPENAI, name=model_name), content=content, usage=usage, provider_payload=payload)

    def _output_text(self, response: Any) -> str:
        text = getattr(response, "output_text", None)
        return text if isinstance(text, str) and text else self._scan_output(response)

    def _scan_output(self, response: Any) -> str:
        for item in getattr(response, "output", []) or []:
            for part in getattr(item, "content", []) or []:
                t = getattr(part, "text", None)
                if isinstance(t, str) and t:
                    return t
        raise ValueError("OpenAI response did not contain text output")

    def _usage(self, response: Any) -> TokenUsage | None:
        u = getattr(response, "usage", None)
        if u is None:
            return None
        return TokenUsage(input_tokens=getattr(u, "input_tokens", None), output_tokens=getattr(u, "output_tokens", None), total_tokens=getattr(u, "total_tokens", None))

    def _payload(self, response: Any) -> Mapping[str, Any]:
        return {"id": getattr(response, "id", None), "model": getattr(response, "model", None)}
