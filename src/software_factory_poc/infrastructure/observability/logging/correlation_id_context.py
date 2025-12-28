from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from uuid import uuid4

_CORRELATION_ID: ContextVar[str | None] = ContextVar("_CORRELATION_ID", default=None)


@dataclass(frozen=True, slots=True)
class CorrelationIdContext:
    def get(self) -> str | None:
        return _CORRELATION_ID.get()

    def set(self, correlation_id: str | None) -> str:
        value = correlation_id or str(uuid4())
        _CORRELATION_ID.set(value)
        return value

    def clear(self) -> None:
        _CORRELATION_ID.set(None)
