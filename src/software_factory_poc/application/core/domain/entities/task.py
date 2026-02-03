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
        """
        import yaml
        import re
        from dataclasses import replace
        import copy

        # 1. Merge Config (Immutable)
        current_config = copy.deepcopy(self.description.config)
        # Deep merge could be better, but for now simple update at root or specific key
        # If new_context has keys that overwrite, they overwrite.
        current_config.update(new_context)

        # 2. Serialize to clean YAML
        new_yaml_str = yaml.dump(current_config, default_flow_style=False, allow_unicode=True).strip()
        formatted_yaml_block = f"```yaml\n{new_yaml_str}\n```"

        # 3. Update Raw Content
        current_raw = self.description.raw_content
        
        # Regex to find existing YAML block: 
        # Supports ```yaml ... ``` or {code:yaml} ... {code} (Jira style)
        # We'll target the standard markdown/jira style we typically assume.
        # Pattern: Start of block, content, End of block
        
        # Pattern 1: Markdown ```yaml
        md_pattern = r"(```yaml\s*)([\s\S]*?)(\s*```)"
        
        if re.search(md_pattern, current_raw, re.IGNORECASE):
            new_raw = re.sub(md_pattern, formatted_yaml_block, current_raw, count=1, flags=re.IGNORECASE)
        else:
            # Append if not found
            new_raw = f"{current_raw.rstrip()}\n\n{formatted_yaml_block}"

        # 4. Return new Task
        new_description = replace(self.description, config=current_config, raw_content=new_raw)
        return replace(self, description=new_description)
