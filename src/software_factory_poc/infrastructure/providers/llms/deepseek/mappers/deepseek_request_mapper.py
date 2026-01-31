from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from software_factory_poc.application.core.agents.reasoner.llm_request import LlmRequest
from software_factory_poc.application.core.agents.reasoner.value_objects.message import Message
from software_factory_poc.application.core.agents.reasoner.value_objects.message_role import MessageRole
from software_factory_poc.application.core.agents.reasoner.value_objects.output_format import OutputFormat


@dataclass(frozen=True)
class DeepSeekRequestMapper:
    def to_kwargs(self, request: LlmRequest) -> Mapping[str, Any]:
        return {
            "model": request.model.name,
            "messages": self._messages(request.messages),
            **self._generation(request),
            **self._output(request),
        }

    def _messages(self, messages: tuple[Message, ...]) -> list[dict[str, str]]:
        return [self._msg(m) for m in messages]

    def _msg(self, message: Message) -> dict[str, str]:
        role = "system" if message.role is MessageRole.DEVELOPER else message.role.value
        return {"role": role, "content": message.content}

    def _generation(self, request: LlmRequest) -> Mapping[str, Any]:
        g = request.generation
        base = {"max_tokens": g.max_output_tokens, "temperature": g.temperature, "top_p": g.top_p, "seed": g.seed, "stop": g.stop}
        return {k: v for k, v in base.items() if v is not None}

    def _output(self, request: LlmRequest) -> Mapping[str, Any]:
        if request.generation.json_mode:
             return {"response_format": {"type": "json_object"}}
             
        if request.output is None or request.output.format is OutputFormat.TEXT:
            return {}
        return {"response_format": {"type": "json_object"}}
