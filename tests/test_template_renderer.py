import pytest
import os
from software_factory_poc.templates.template_registry_service import TemplateRegistryService
from software_factory_poc.templates.template_file_loader_service import TemplateFileLoaderService
from software_factory_poc.templates.template_renderer_service import TemplateRendererService

def test_renderer_happy_path(settings):
    # Setup template
    t_id = "render_test"
    t_dir = settings.template_catalog_root / t_id
    os.makedirs(t_dir, exist_ok=True)
    
    (t_dir / "template_manifest.yaml").write_text("""
template_version: "1"
description: "Render Test"
expected_paths: ["out.txt"]
""")
    (t_dir / "out.txt.j2").write_text("Val: {{ my_var }}")

    # Build services
    registry = TemplateRegistryService(settings)
    loader = TemplateFileLoaderService()
    renderer = TemplateRendererService(registry, loader)

    # Execute
    files = renderer.render(t_id, {"my_var": "123"})
    assert files["out.txt"] == "Val: 123"

def test_renderer_missing_var(settings):
    t_id = "missing_var"
    t_dir = settings.template_catalog_root / t_id
    os.makedirs(t_dir, exist_ok=True)
    (t_dir / "template_manifest.yaml").write_text("""
template_version: "1"
description: "Fail"
expected_paths: ["out.txt"]
""")
    (t_dir / "out.txt.j2").write_text("{{ missing }}")

    registry = TemplateRegistryService(settings)
    loader = TemplateFileLoaderService()
    renderer = TemplateRendererService(registry, loader)

    with pytest.raises(ValueError) as exc:
        renderer.render(t_id, {})
    assert "undefined" in str(exc.value)
