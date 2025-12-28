from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from llm_bridge.core.entities.llm_response import LlmResponse
from llm_bridge.core.value_objects.model_id import ModelId
from llm_bridge.core.value_objects.provider_name import ProviderName
from llm_bridge.core.value_objects.token_usage import TokenUsage


@dataclass(frozen=True, slots=True)
class DeepSeekResponseMapper:
    def to_domain(self, model_name: str, response: Any) -> LlmResponse:
        msg = self._message(response)
        content = self._content(msg)
        reasoning = getattr(msg, "reasoning_content", None)
        usage = self._usage(response)
        return LlmResponse(model=ModelId(provider=ProviderName.DEEPSEEK, name=model_name), content=content, usage=usage, provider_payload=self._payload(response), reasoning_content=reasoning)

    def _message(self, response: Any) -> Any:
        choices = getattr(response, "choices", None) or []
        if not choices:
            raise ValueError("DeepSeek response had no choices")
        return getattr(choices[0], "message", None)

    def _content(self, message: Any) -> str:
        text = getattr(message, "content", None)
        if isinstance(text, str) and text.strip():
            return text.strip()
        raise ValueError("DeepSeek response did not contain content")

    def _usage(self, response: Any) -> TokenUsage | None:
        u = getattr(response, "usage", None)
        if u is None:
            return None
        return TokenUsage(input_tokens=getattr(u, "prompt_tokens", None), output_tokens=getattr(u, "completion_tokens", None), total_tokens=getattr(u, "total_tokens", None))

    def _payload(self, response: Any) -> Mapping[str, Any]:
        return {"id": getattr(response, "id", None), "model": getattr(response, "model", None)}
