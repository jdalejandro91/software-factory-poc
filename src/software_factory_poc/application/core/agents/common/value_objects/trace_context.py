from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from uuid import uuid4


@dataclass(frozen=True)
class TraceContext:
    correlation_id: str
    request_id:Optional[ str] = None

    @staticmethod
    def create() -> TraceContext:
        return TraceContext(correlation_id=str(uuid4()))
