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

    def _merge_dictionaries(self, target: Dict[str, Any], source: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively merges source dictionary into target dictionary.
        """
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._merge_dictionaries(target[key], value)
            else:
                target[key] = value
        return target

    def update_metadata(self, new_context: Dict[str, Any]) -> "Task":
        """
        Creates a new Task instance with merged configuration.
        Does NOT modify raw_content string (assumes it is pure text).
        """
        from dataclasses import replace
        import copy

        # 1. Merge Config (Deep Merge)
        current_config = copy.deepcopy(self.description.config)
        self._merge_dictionaries(current_config, new_context)

        # 2. Return new Task with updated config but same raw_content
        new_description = replace(self.description, config=current_config, raw_content=self.description.raw_content)
        return replace(self, description=new_description)
