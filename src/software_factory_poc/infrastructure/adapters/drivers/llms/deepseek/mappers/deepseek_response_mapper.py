from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Optional

from software_factory_poc.application.ports.drivers.common.config.llm_provider_type import LlmProviderType
from software_factory_poc.application.ports.drivers.common.value_objects.model_id import ModelId
from software_factory_poc.application.ports.drivers.reasoner import LlmResponse
from software_factory_poc.application.ports.drivers.reasoner import TokenMetric


@dataclass(frozen=True)
class DeepSeekResponseMapper:
    def to_domain(self, model_name: str, response: Any) -> LlmResponse:
        msg = self._message(response)
        content = self._content(msg)
        reasoning = getattr(msg, "reasoning_content", None)
        usage = self._usage(response)
        return LlmResponse(model=ModelId(provider=LlmProviderType.DEEPSEEK, name=model_name), content=content, usage=usage, provider_payload=self._payload(response), reasoning_content=reasoning)

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

    def _usage(self, response: Any) ->Optional[ TokenMetric]:
        u = getattr(response, "usage", None)
        if u is None:
            return None
        return TokenMetric(input_tokens=getattr(u, "prompt_tokens", None), output_tokens=getattr(u, "completion_tokens", None), total_tokens=getattr(u, "total_tokens", None))

    def _payload(self, response: Any) -> Mapping[str, Any]:
        return {"id": getattr(response, "id", None), "model": getattr(response, "model", None)}
