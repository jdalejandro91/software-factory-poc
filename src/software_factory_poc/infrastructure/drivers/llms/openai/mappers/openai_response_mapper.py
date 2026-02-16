from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Optional

from software_factory_poc.application.drivers.common.config.llm_provider_type import LlmProviderType
from software_factory_poc.application.drivers.common import ModelId
from software_factory_poc.application.drivers.brain import LlmResponse
from software_factory_poc.application.drivers.brain import TokenMetric


@dataclass(frozen=True)
class OpenAiResponseMapper:
    def to_domain(self, model_name: str, response: Any) -> LlmResponse:
        try:
            choice = response.choices[0]
            content = choice.message.content
            
            if not content:
                finish_reason = getattr(choice, 'finish_reason', 'unknown')
                if finish_reason == "content_filter":
                    raise ValueError("OpenAI validation failed: content_filter triggered. Response blocked for security.")
                if finish_reason == "length":
                    raise ValueError("OpenAI validation failed: Max tokens exceeded (length). Incomplete JSON.")
                raise ValueError(f"OpenAI returned empty content. Finish reason: {finish_reason}")
            
            # Sanitization: Strip markdown code blocks if present
            # This is a safe default for JSON mode
            if content.strip().startswith("```"):
                 import re
                 content = re.sub(r"^```(?:json)?\s*", "", content.strip())
                 content = re.sub(r"\s*```$", "", content)

            payload = self._payload(response)
            usage = self._usage(response)
            
            return LlmResponse(model=ModelId(provider=LlmProviderType.OPENAI, name=model_name), content=content, usage=usage, provider_payload=payload)

        except Exception as e:
            raise ValueError(f"Failed to map OpenAI response: {e}")

    def _usage(self, response: Any) ->Optional[ TokenMetric]:
        u = getattr(response, "usage", None)
        if u is None:
            return None
        return TokenMetric(input_tokens=getattr(u, "input_tokens", None), output_tokens=getattr(u, "output_tokens", None), total_tokens=getattr(u, "total_tokens", None))

    def _payload(self, response: Any) -> Mapping[str, Any]:
        return {"id": getattr(response, "id", None), "model": getattr(response, "model", None)}
