from __future__ import annotations
from typing import Optional

from dataclasses import dataclass


@dataclass(frozen=True)
class TokenMetric:
    input_tokens:Optional[ int] = None
    output_tokens:Optional[ int] = None
    total_tokens:Optional[ int] = None
