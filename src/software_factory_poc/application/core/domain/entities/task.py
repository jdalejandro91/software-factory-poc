from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List

@dataclass
class TaskDescription:
    """
    Entidad que encapsula la descripción técnica procesada de la tarea.
    - raw_content: El texto original de la descripción (Markdown/Jira markup) para auditoría.
    - config: El diccionario resultante del parseo del bloque YAML (scaffolding/code_review).
    """
    raw_content: str
    config: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TaskUser:
    name: str
    display_name: str
    active: bool
    email: Optional[str] = None
    self_url: Optional[str] = None

@dataclass
class Task:
    id: str
    key: str
    summary: str
    status: str
    project_key: str
    issue_type: str
    description: TaskDescription  # Composición Obligatoria
    reporter: Optional[TaskUser] = None
    event_type: Optional[str] = None
    created_at: Optional[int] = None
