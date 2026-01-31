from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class TokenMetric:
    input_tokens:Optional[ int] = None
    output_tokens:Optional[ int] = None
    total_tokens:Optional[ int] = None
