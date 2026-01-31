from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from typing import Optional
from uuid import uuid4

_CORRELATION_ID:Optional[ ContextVar[str]] = ContextVar("_CORRELATION_ID", default=None)


@dataclass(frozen=True)
class CorrelationIdContext:
    def get(self) ->Optional[ str]:
        return _CORRELATION_ID.get()

    def set(self, correlation_id:Optional[ str]) -> str:
        value = correlation_id or str(uuid4())
        _CORRELATION_ID.set(value)
        return value

    def clear(self) -> None:
        _CORRELATION_ID.set(None)
