from dataclasses import dataclass


@dataclass
class IdempotencyRecord:
    key: str
    mr_url: str
