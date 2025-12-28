from __future__ import annotations

from dataclasses import dataclass

from software_factory_poc.core.value_objects.message_role import MessageRole


@dataclass(frozen=True, slots=True)
class Message:
    role: MessageRole
    content: str

    def __post_init__(self) -> None:
        if not self.content:
            raise ValueError("Message.content must be non-empty")
