from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class TraceContext:
    correlation_id: str
    request_id: str | None = None

    @staticmethod
    def create() -> "TraceContext":
        return TraceContext(correlation_id=str(uuid4()))
