from dataclasses import dataclass, field
from typing import Any


@dataclass
class TaskDescription:
    """
    Entidad que encapsula la descripción técnica procesada de la tarea.
    - raw_content: El texto original de la descripción (Markdown/Jira markup) para auditoría.
    - config: El diccionario resultante del parseo del bloque YAML (scaffolder/code_review).
    """
    raw_content: str
    config: dict[str, Any] = field(default_factory=dict)