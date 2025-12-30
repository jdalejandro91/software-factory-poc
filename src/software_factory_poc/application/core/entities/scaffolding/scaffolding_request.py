from dataclasses import dataclass

@dataclass(frozen=True)
class ScaffoldingRequest:
    issue_key: str
    project_key: str
    summary: str
    raw_instruction: str
    reporter: str
