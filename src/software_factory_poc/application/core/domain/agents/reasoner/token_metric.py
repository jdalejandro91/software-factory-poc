from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TokenMetric:
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
