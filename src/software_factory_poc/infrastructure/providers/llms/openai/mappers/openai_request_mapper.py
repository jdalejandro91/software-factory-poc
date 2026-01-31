from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from software_factory_poc.application.core.agents.reasoner.llm_request import LlmRequest
from software_factory_poc.application.core.agents.reasoner.value_objects.message import Message
from software_factory_poc.application.core.agents.reasoner.value_objects.message_role import MessageRole
from software_factory_poc.application.core.agents.reasoner.value_objects.output_format import OutputFormat


@dataclass(frozen=True)
class OpenAiRequestMapper:
    def to_kwargs(self, request: LlmRequest) -> Mapping[str, Any]:
        messages = self._input_messages(request.messages)
        
        # Defensive Injection: Ensure "JSON" keyword exists if JSON mode is requested
        if request.generation.json_mode:
            has_json_keyword = any("json" in m["content"].lower() for m in messages)
            if not has_json_keyword:
                messages = [{"role": "system", "content": "IMPORTANT: Output valid JSON."}] + messages

        return {
            "model": request.model.name,
            "messages": messages,
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
        # Mapeo explícito de dominio -> proveedor
        params = {
            "max_tokens": g.max_output_tokens,
            "temperature": g.temperature,
            "top_p": g.top_p,
            "seed": g.seed,
            "stop": g.stop
        }
        # Filtrar None
        return {k: v for k, v in params.items() if v is not None}

    def _output_kwargs(self, request: LlmRequest) -> Mapping[str, Any]:
        # Use generation config property which checks format == JSON
        if request.generation.json_mode:
            return {"response_format": {"type": "json_object"}}
        
        # Legacy/Additional OutputConstraints logic (if needed in future)
        if request.output and request.output.format is OutputFormat.JSON:
             return {"response_format": {"type": "json_object"}}
            
        return {}

