from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from software_factory_poc.application.drivers.brain import LlmRequest
from software_factory_poc.application.drivers.brain.value_objects.message import Message
from software_factory_poc.application.drivers.brain.value_objects.message_role import MessageRole
from software_factory_poc.application.drivers.brain import OutputFormat


@dataclass(frozen=True)
class GeminiRequestMapper:
    def to_kwargs(self, request: LlmRequest) -> Mapping[str, Any]:
        # 1. Sanitize model name
        model_name = request.model.name
        if model_name.startswith("models/"):
            model_name = model_name.replace("models/", "")

        return {
            "model": model_name,
            "contents": self._prompt(request.messages),
            "config": self._config(request)
        }

    def _prompt(self, messages: tuple[Message, ...]) -> str:
        lines = [self._line(m) for m in messages]
        return "\n".join([l for l in lines if l]).strip()

    def _line(self, message: Message) -> str:
        if message.role is MessageRole.SYSTEM:
            return f"[SYSTEM] {message.content}"
        if message.role is MessageRole.DEVELOPER:
            return f"[DEVELOPER] {message.content}"
        return f"[{message.role.value.upper()}] {message.content}"

    def _config(self, request: LlmRequest) -> dict[str, Any]:
        base = {
            "max_output_tokens": request.generation.max_output_tokens,
            "temperature": request.generation.temperature,
            "top_p": request.generation.top_p,
            "seed": request.generation.seed
        }
        cfg = {k: v for k, v in base.items() if v is not None}
        
        if request.generation.format == OutputFormat.JSON:
            cfg["response_mime_type"] = "application/json"
        else:
            cfg["response_mime_type"] = "text/plain"
            
        return cfg
