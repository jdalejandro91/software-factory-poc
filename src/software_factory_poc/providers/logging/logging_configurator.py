from __future__ import annotations

import logging
import logging.config
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from software_factory_poc.providers.logging.correlation_id_context import CorrelationIdContext
from software_factory_poc.providers.logging.correlation_id_filter import CorrelationIdFilter


@dataclass(frozen=True, slots=True)
class LoggingConfigurator:
    context: CorrelationIdContext

    def configure(self, base_level: str = "INFO") -> None:
        logging.config.dictConfig(self._dict_config(base_level))

    def _dict_config(self, base_level: str) -> Mapping[str, Any]:
        return {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {"cid": {"()": CorrelationIdFilter, "context": self.context}},
            "formatters": {"std": {"format": "%(asctime)s %(levelname)s %(name)s [cid=%(correlation_id)s] %(message)s"}},
            "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "std", "filters": ["cid"]}},
            "root": {"handlers": ["console"], "level": base_level},
        }
