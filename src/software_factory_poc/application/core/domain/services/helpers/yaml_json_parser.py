import json
import yaml
from typing import Any

class YamlJsonParser:
    """
    Parses content as YAML or JSON.
    """
    
    @staticmethod
    def parse(content: str) -> dict[str, Any]:
        # Try YAML (Priority)
        try:
            parsed = yaml.safe_load(content)
            if isinstance(parsed, dict):
                return parsed
        except yaml.YAMLError:
            pass

        # Try JSON
        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        raise ValueError("Could not parse valid YAML or JSON from content.")
