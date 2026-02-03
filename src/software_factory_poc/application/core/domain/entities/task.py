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

    def update_metadata(self, new_context: Dict[str, Any]) -> "Task":
        """
        Creates a new Task instance with merged configuration and updated raw content.
        Safely preserves existing human text while updating the automation YAML block.
        Preserves the formatting style (Jira {code} vs Markdown ```).
        """
        import yaml
        import re
        from dataclasses import replace
        import copy

        # 1. Merge Config (Immutable)
        current_config = copy.deepcopy(self.description.config)
        
        # Smart Merge: Specifically handle 'code_review_params' to preserve existing sub-keys
        for key, value in new_context.items():
            if key == "code_review_params" and isinstance(value, dict) and \
               key in current_config and isinstance(current_config[key], dict):
                current_config[key].update(value)
            else:
                current_config[key] = value

        # 2. Serialize to clean YAML
        new_yaml_str = yaml.dump(current_config, default_flow_style=False, allow_unicode=True).strip()

        # 3. Detect and Preserve Block Style
        current_raw = self.description.raw_content
        
        # Robust Regex to capture delimiters
        # Captures: start=Opening Tag, content=Content, end=Closing Tag
        # Support: ```yaml, ```, {code:yaml}, {code}
        complex_pattern = r"(?P<start>```(?:yaml|yml|scaffolding)?|\{code(?::(?:yaml|yml|scaffolding))?(?:\|[\w=]+)*\})\s*(?P<content>[\s\S]*?)\s*(?P<end>```|\{code\})"
        
        match = re.search(complex_pattern, current_raw, re.IGNORECASE)
        
        if match:
            start_tag = match.group("start")
            end_tag = match.group("end")
            
            # Normalize Jira tag if complex to ensure valid YAML structure or reuse exact?
            # We reuse the exact captured tag to minimize diffs, assuming it was valid.
            
            new_block = f"{start_tag}\n{new_yaml_str}\n{end_tag}"
            
            # Replace the full match with the new block
            new_raw = current_raw.replace(match.group(0), new_block)
            
        else:
            # Default to Jira style if no block found (Safer for Jira rendering)
            start_tag = "{code:yaml}"
            end_tag = "{code}"
            
            formatted_yaml_block = f"{start_tag}\n{new_yaml_str}\n{end_tag}"
            new_raw = f"{current_raw.rstrip()}\n\n{formatted_yaml_block}"

        # 4. Return new Task
        new_description = replace(self.description, config=current_config, raw_content=new_raw)
        return replace(self, description=new_description)
