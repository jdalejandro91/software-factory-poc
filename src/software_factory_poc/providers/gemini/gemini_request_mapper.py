from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from llm_bridge.core.entities.llm_request import LlmRequest
from llm_bridge.core.value_objects.message import Message
from llm_bridge.core.value_objects.message_role import MessageRole
from llm_bridge.core.value_objects.output_format import OutputFormat


@dataclass(frozen=True, slots=True)
class GeminiRequestMapper:
    def to_kwargs(self, request: LlmRequest) -> Mapping[str, Any]:
        return {"model": request.model.name, "contents": self._prompt(request.messages), "config": self._config(request)}

    def _prompt(self, messages: tuple[Message, ...]) -> str:
        lines = [self._line(m) for m in messages]
        return "\n".join([l for l in lines if l]).strip()

    def _line(self, message: Message) -> str:
        if message.role is MessageRole.SYSTEM:
            return f"[SYSTEM] {message.content}"
        if message.role is MessageRole.DEVELOPER:
            return f"[DEVELOPER] {message.content}"
        return f"[{message.role.value.upper()}] {message.content}"

    def _config(self, request: LlmRequest):
        try:
            from google.genai import types
        except ImportError:  # pragma: no cover
            return None
        base = {"max_output_tokens": request.generation.max_output_tokens, "temperature": request.generation.temperature, "top_p": request.generation.top_p, "seed": request.generation.seed}
        cfg = {k: v for k, v in base.items() if v is not None}
        if request.output is None or request.output.format is OutputFormat.TEXT:
            return types.GenerateContentConfig(**cfg)
        return types.GenerateContentConfig(**cfg, **self._output_cfg(request, types))

    def _output_cfg(self, request: LlmRequest, types: Any) -> Mapping[str, Any]:
        if request.output.format is OutputFormat.JSON_SCHEMA and request.output.schema is not None:
            return {"response_mime_type": "application/json", "response_json_schema": dict(request.output.schema.json_schema)}
        return {"response_mime_type": "application/json", "response_json_schema": {"type": "object"}}
