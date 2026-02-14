from dataclasses import dataclass


@dataclass(frozen=True)
class ScaffoldingOrder:
    issue_key: str
    raw_instruction: str
    technology_stack: str = "nestJS" # Default or Optional
    repository_url: str = ""
    project_id: str = ""
    target_config: dict = None
    extra_params: dict = None
    service_name: str = None # Optional explicit field
    # Legacy fields
    summary: str = ""
    reporter: str = ""
    project_key: str = ""
    
    def __post_init__(self):
        # Workaround for mutable defaults in dataclass if needed, 
        # but since frozen=True and we assign in mapper, None is safer default
        pass
