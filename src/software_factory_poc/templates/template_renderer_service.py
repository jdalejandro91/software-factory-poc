from typing import Any, Dict

from jinja2 import Environment, StrictUndefined, BaseLoader

from software_factory_poc.templates.template_file_loader_service import TemplateFileLoaderService
from software_factory_poc.templates.template_manifest_model import TemplateManifestModel
from software_factory_poc.templates.template_registry_service import TemplateRegistryService


class TemplateRendererService:
    def __init__(
        self,
        registry: TemplateRegistryService,
        loader: TemplateFileLoaderService,
    ):
        self.registry = registry
        self.loader = loader
        # Use StrictUndefined to raise errors for missing variables
        self.jinja_env = Environment(loader=BaseLoader(), undefined=StrictUndefined)

    def render(self, template_id: str, context: Dict[str, Any]) -> Dict[str, str]:
        """
        Orchestrates the loading and rendering of a template.
        Returns a dict mapping {relative_path: rendered_content}.
        """
        # 1. Resolve directory
        template_dir = self.registry.resolve_template_dir(template_id)
        
        # 2. Load manifest
        manifest = self.loader.load_manifest(template_dir)
        
        # 3. Load all .j2 files
        raw_files = self.loader.load_j2_files(template_dir)
        
        files_map = {}
        
        # 4. Render
        for target_path, raw_content in raw_files:
            try:
                # We interpret the path itself as a template too, to allow dynamic filenames?
                # The user request didn't specify dynamic filenames, but standard practice often allows it.
                # For PoC simplicity and determinism per user spec, let's assume static filenames mostly,
                # but Jinja render on content is mandatory.
                
                # Check if strict requirements allow path rendering. 
                # "template_file_loader_service: ... returns (relative_path_without_.j2, template_text)"
                # "renderer: render(template_id, vars) -> ... files_map: dict[path]=content"
                # Let's keep paths static for now unless explicitly requested.
                
                template = self.jinja_env.from_string(raw_content)
                rendered_content = template.render(**context)
                files_map[target_path] = rendered_content
            except Exception as e:
                # Wrap errors with context
                raise ValueError(f"Error rendering {target_path}: {str(e)}") from e
        
        # 5. Validate expected paths
        self._validate_expected_paths(manifest, files_map)
        
        return files_map

    def _validate_expected_paths(self, manifest: TemplateManifestModel, files_map: Dict[str, str]):
        missing = []
        for expected in manifest.expected_paths:
            if expected not in files_map:
                missing.append(expected)
        
        if missing:
            raise ValueError(f"Template '{manifest.description}' failed validation. Missing expected paths: {missing}")
