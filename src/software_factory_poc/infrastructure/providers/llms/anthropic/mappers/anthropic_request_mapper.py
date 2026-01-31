from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from software_factory_poc.application.core.agents.reasoner.llm_request import LlmRequest
from software_factory_poc.application.core.agents.reasoner.value_objects.message import Message
from software_factory_poc.application.core.agents.reasoner.value_objects.message_role import MessageRole
from software_factory_poc.application.core.agents.reasoner.value_objects.output_format import OutputFormat


@dataclass(frozen=True)
class AnthropicRequestMapper:
    def to_kwargs(self, request: LlmRequest) -> Mapping[str, Any]:
        return {
            "model": request.model.name,
            "max_tokens": self._max_tokens(request),
            "system": self._system(request),
            "messages": self._messages(request.messages),
        }

    def _max_tokens(self, request: LlmRequest) -> int:
        return request.generation.max_output_tokens or 1024

    def _system(self, request: LlmRequest) -> str:
        base = self._join_system(request.messages)
        return self._with_output_hint(base, request)

    def _join_system(self, messages: tuple[Message, ...]) -> str:
        sys_msgs = [m.content for m in messages if m.role in (MessageRole.SYSTEM, MessageRole.DEVELOPER)]
        return "\n".join(sys_msgs).strip()

    def _messages(self, messages: tuple[Message, ...]) -> list[dict[str, str]]:
        return [self._msg(m) for m in messages if m.role not in (MessageRole.SYSTEM, MessageRole.DEVELOPER)]

    def _msg(self, message: Message) -> dict[str, str]:
        return {"role": message.role.value, "content": message.content}

    def _with_output_hint(self, system_text: str, request: LlmRequest) -> str:
        if request.output is None or request.output.format is OutputFormat.TEXT:
            return system_text
        return (system_text + "\n\nReturn a valid JSON object only.").strip()
