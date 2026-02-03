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

    def _generate_yaml_block(self, data: Dict[str, Any], start_tag: str, end_tag: str) -> str:
        """
        Generates a clean YAML block encapsulated in tags.
        """
        import yaml
        yaml_str = yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False).strip()
        return f"{start_tag}\n{yaml_str}\n{end_tag}"

    def update_metadata(self, new_context: Dict[str, Any]) -> "Task":
        """
        Creates a new Task instance with merged configuration and updated raw content.
        Safely preserves existing human text while updating the automation YAML block.
        Preserves the formatting style (Jira {code} vs Markdown ```).
        """
        import re
        from dataclasses import replace
        import copy

        # 1. Merge Config (Deep Merge)
        current_config = copy.deepcopy(self.description.config)
        self._merge_dictionaries(current_config, new_context)

        # 2. Detect and Preserve Block Style
        current_raw = self.description.raw_content
        
        # Robust Regex to capture delimiters
        complex_pattern = r"(?P<start>```(?:yaml|yml|scaffolding)?|\{code(?::(?:yaml|yml|scaffolding))?(?:\|[\w=]+)*\})\s*(?P<content>[\s\S]*?)\s*(?P<end>```|\{code\})"
        
        match = re.search(complex_pattern, current_raw, re.IGNORECASE)
        
        if match:
            start_tag = match.group("start")
            end_tag = match.group("end")
            
            # Generate new block
            new_block = self._generate_yaml_block(current_config, start_tag, end_tag)
            
            # Surgical Replacement
            new_raw = current_raw.replace(match.group(0), new_block, 1)
            
        else:
            # Default to Jira style if no block found
            start_tag = "{code:yaml}"
            end_tag = "{code}"
            
            formatted_yaml_block = self._generate_yaml_block(current_config, start_tag, end_tag)
            new_raw = f"{current_raw.rstrip()}\n\n{formatted_yaml_block}"

        # 3. Return new Task
        new_description = replace(self.description, config=current_config, raw_content=new_raw)
        return replace(self, description=new_description)
