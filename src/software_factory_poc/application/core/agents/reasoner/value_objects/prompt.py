from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Prompt:
    system_message: str
    user_message: str
    response_format_hints:Optional[ str] = None
