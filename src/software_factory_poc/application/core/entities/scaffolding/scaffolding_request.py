from dataclasses import dataclass

@dataclass(frozen=True)
class ScaffoldingRequest:
    ticket_id: str
    project_key: str
    summary: str
    raw_instruction: str
    requester: str
