from __future__ import annotations

import logging
from dataclasses import dataclass

from llm_bridge.providers.logging.correlation_id_context import CorrelationIdContext


@dataclass(frozen=True, slots=True)
class CorrelationIdFilter(logging.Filter):
    context: CorrelationIdContext

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = self.context.get() or "-"
        return True
