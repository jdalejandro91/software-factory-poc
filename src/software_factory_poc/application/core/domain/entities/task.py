from dataclasses import dataclass, field
from typing import Any, Dict, Optional

@dataclass(frozen=True)
class TaskDescription:
    """
    Value Object representing the processed description of a Task.
    Contains both the raw content for audit and the parsed configuration.
    """
    raw_content: str
    config: Dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class TaskUser:
    """
    Value Object representing a User in the context of a Task.
    """
    name: str
    display_name: str
    active: bool = True
    email: Optional[str] = None

@dataclass
class Task:
    """
    Domain Entity representing a Task (Issue) in the system.
    """
    id: str
    key: str
    event_type: str
    status: str
    summary: str
    project_key: str
    issue_type: str
    created_at: Any  # Can be int (timestamp) or datetime
    reporter: TaskUser
    description: TaskDescription

    def __post_init__(self):
        # Basic validation or defaults could go here if needed
        pass
