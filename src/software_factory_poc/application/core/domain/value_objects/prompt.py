from dataclasses import dataclass


@dataclass(frozen=True)
class Prompt:
    system_message: str
    user_message: str
    response_format_hints: str | None = None
