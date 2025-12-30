from dataclasses import dataclass


@dataclass(frozen=True)
class ScaffoldingRequest:
    issue_key: str
    raw_instruction: str
    technology_stack: str = "python" # Default or Optional
    repository_url: str = ""
    project_id: str = ""
    # Legacy fields kept optional or removed if unused?
    # Keeping summary/reporter for now to avoid breaking other parsers if they exist, but making optional
    summary: str = ""
    reporter: str = ""
    project_key: str = ""
