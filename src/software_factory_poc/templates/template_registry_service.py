from pathlib import Path

from software_factory_poc.config.settings_pydantic import Settings


class TemplateRegistryService:
    def __init__(self, settings: Settings):
        self.settings = settings

    def resolve_template_dir(self, template_id: str) -> Path:
        """
        Resolves the absolute path to the template directory and strictly verifies it exists.
        """
        if not template_id:
            raise ValueError("template_id cannot be empty")
        
        # Sanitize template_id to prevent path traversal
        clean_id = template_id.replace("..", "").replace("/", "").replace("\\", "")
        
        template_dir = self.settings.template_catalog_root / clean_id
        
        if not template_dir.exists():
            raise FileNotFoundError(f"Template directory not found: {template_dir}")
        
        if not template_dir.is_dir():
            raise NotADirectoryError(f"Template path is not a directory: {template_dir}")
            
        return template_dir
