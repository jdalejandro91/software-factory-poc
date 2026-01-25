from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Optional

from software_factory_poc.application.core.agents.reasoner.llm_response import LlmResponse
from software_factory_poc.application.core.agents.common.value_objects.model_id import ModelId
from software_factory_poc.application.core.agents.common.config.llm_provider_type import LlmProviderType
from software_factory_poc.application.core.agents.reasoner.token_metric import TokenMetric


@dataclass(frozen=True)
class GeminiResponseMapper:
    def to_domain(self, model_name: str, response: Any) -> LlmResponse:
        text = self._text(response)
        usage = self._usage(response)
        return LlmResponse(model=ModelId(provider=LlmProviderType.GEMINI, name=model_name), content=text, usage=usage, provider_payload=self._payload(response))

    def _text(self, response: Any) -> str:
        text = getattr(response, "text", None)
        if isinstance(text, str) and text.strip():
            return text.strip()
        raise ValueError("Gemini response did not contain text output")

    def _usage(self, response: Any) ->Optional[ TokenMetric]:
        meta = getattr(response, "usage_metadata", None)
        if meta is None:
            return None
        return TokenMetric(input_tokens=getattr(meta, "prompt_token_count", None), output_tokens=getattr(meta, "candidates_token_count", None), total_tokens=getattr(meta, "total_token_count", None))

    def _payload(self, response: Any) -> Mapping[str, Any]:
        return {"model": getattr(response, "model_version", None)}
