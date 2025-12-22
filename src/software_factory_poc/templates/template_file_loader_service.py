from pathlib import Path
from typing import List, Tuple

import yaml

from software_factory_poc.templates.template_manifest_model import TemplateManifestModel


class TemplateFileLoaderService:
    def load_manifest(self, template_dir: Path) -> TemplateManifestModel:
        """
        Loads and validates the template_manifest.yaml
        """
        manifest_path = template_dir / "template_manifest.yaml"
        if not manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found in {template_dir}")
            
        with open(manifest_path, "r") as f:
            try:
                data = yaml.safe_load(f)
            except yaml.YAMLError as e:
                raise ValueError(f"Invalid YAML in manifest: {e}")
                
        return TemplateManifestModel(**data)

    def load_j2_files(self, template_dir: Path) -> List[Tuple[str, str]]:
        """
        Recursively scans template_dir for .j2 files.
        Returns a list of tuples: (relative_path_without_extension, raw_content)
        """
        j2_files = []
        
        # Iterate over all files recursively
        for path in template_dir.rglob("*.j2"):
            if not path.is_file():
                continue
            
            # Read content
            content = path.read_text(encoding="utf-8")
            
            # Compute relative path from template root
            rel_path = path.relative_to(template_dir)
            
            # Strip .j2 extension for the target path
            # If filename is "foo.py.j2", it becomes "foo.py"
            target_path_str = str(rel_path)[:-3] 
            
            j2_files.append((target_path_str, content))
            
        return j2_files
