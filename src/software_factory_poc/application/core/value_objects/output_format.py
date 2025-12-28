from __future__ import annotations

from enum import Enum


class OutputFormat(str, Enum):
    TEXT = "text"
    JSON_OBJECT = "json_object"
    JSON_SCHEMA = "json_schema"
