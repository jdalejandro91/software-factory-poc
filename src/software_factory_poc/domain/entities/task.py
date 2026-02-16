from dataclasses import dataclass
from typing import Dict, Any, Optional

from software_factory_poc.domain.value_objects.task.task_description import TaskDescription
from software_factory_poc.domain.value_objects.task.task_user import TaskUser


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

    @property
    def merge_request_iid(self) -> str | None:
        """Helper para extraer de forma segura el IID del Merge Request de la config YAML"""
        val = self.description.config.get("merge_request_iid")
        return str(val) if val else None