from pathlib import Path

import pytest

from software_factory_poc.application.core.domain.exceptions.provider_error import ProviderError
from software_factory_poc.application.core.domain.configuration.knowledge_provider_type import KnowledgeProviderType
from software_factory_poc.infrastructure.providers.knowledge.filesystem_knowledge_adapter import (
    FileSystemKnowledgeAdapter,
)

# We use the real assets folder created in the previous step for integration-like unit test
# or we could use tmp_path fixture. Using real assets confirms wiring.

def test_retrieve_existing_template():
    base_path = Path("assets")
    adapter = FileSystemKnowledgeAdapter(base_path)
    
    # Query relative to base_path
    content = adapter.retrieve_context("templates/nestjs-base/README.md")
    
    assert "# NestJS Base Template" in content
    assert "src/main.ts" in content

def test_retrieve_non_existent_file():
    base_path = Path("assets")
    adapter = FileSystemKnowledgeAdapter(base_path)
    
    with pytest.raises(ProviderError) as exc:
        adapter.retrieve_context("templates/does-not-exist.md")
    
    # ProviderError wrap
    assert exc.value.provider == KnowledgeProviderType.FILE_SYSTEM
    assert "File not found" in exc.value.message

def test_security_directory_traversal():
    base_path = Path("assets")
    adapter = FileSystemKnowledgeAdapter(base_path)
    
    # Try to access ../.env or similar
    with pytest.raises(ProviderError) as exc:
        adapter.retrieve_context("../.env")
        
    assert "Invalid file query path" in exc.value.message
