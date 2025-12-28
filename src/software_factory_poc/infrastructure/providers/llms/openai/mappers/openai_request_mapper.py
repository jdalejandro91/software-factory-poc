from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from software_factory_poc.application.core.entities.llm_request import LlmRequest
from software_factory_poc.application.core.value_objects.message import Message
from software_factory_poc.application.core.value_objects.message_role import MessageRole
from software_factory_poc.application.core.value_objects.output_format import OutputFormat


@dataclass(frozen=True, slots=True)
class OpenAiRequestMapper:
    def to_kwargs(self, request: LlmRequest) -> Mapping[str, Any]:
        return {
            "model": request.model.name,
            "input": self._input_messages(request.messages),
            **self._generation_kwargs(request),
            **self._output_kwargs(request),
        }

    def _input_messages(self, messages: tuple[Message, ...]) -> list[dict[str, str]]:
        return [self._msg(m) for m in messages]

    def _msg(self, message: Message) -> dict[str, str]:
        role = message.role.value if message.role is not MessageRole.SYSTEM else "system"
        return {"role": role, "content": message.content}

    def _generation_kwargs(self, request: LlmRequest) -> Mapping[str, Any]:
        g = request.generation
        return {k: v for k, v in {"max_output_tokens": g.max_output_tokens, "temperature": g.temperature, "top_p": g.top_p, "seed": g.seed, "stop": g.stop}.items() if v is not None}

    def _output_kwargs(self, request: LlmRequest) -> Mapping[str, Any]:
        if request.output is None:
            return {}
        fmt = request.output.format
        if fmt is OutputFormat.TEXT:
            return {"text": {"format": {"type": "text"}}}
        if fmt is OutputFormat.JSON_OBJECT:
            return {"text": {"format": {"type": "json_object"}}}
        schema = request.output.schema
        return {"text": {"format": {"type": "json_schema", "name": schema.name, "schema": schema.json_schema, "strict": schema.strict}}}  # type: ignore[union-attr]
