
import pytest
from software_factory_poc.application.core.domain.services.helpers.text_block_extractor import TextBlockExtractor

class TestTextBlockExtractor:
    
    def test_extract_markdown_basic(self):
        text = """
Some intro text.
```scaffolding
version: "1.0"
technology_stack: "python"
service_slug: "test-service"
```
Outro text.
"""
        extracted = TextBlockExtractor.extract_block(text)
        assert extracted is not None
        assert 'version: "1.0"' in extracted
        assert 'technology_stack: "python"' in extracted

    def test_extract_markdown_windows_lines(self):
        # \r\n line endings
        text = "Intro.\r\n```scaffolding\r\nversion: \"1.0\"\r\ntechnology_stack: \"go\"\r\nservice_slug: \"win-service\"\r\n```\r\nOutro."
        extracted = TextBlockExtractor.extract_block(text)
        assert extracted is not None
        assert 'version: "1.0"' in extracted
        assert 'service_slug: "win-service"' in extracted

    def test_extract_markdown_extra_spaces(self):
        # Spaces after ``` and language tag
        text = """
```  scaffolding   
version: "1.0"
technology_stack: "node"
service_slug: "space-service"

```
"""
        extracted = TextBlockExtractor.extract_block(text)
        assert extracted is not None
        assert 'version: "1.0"' in extracted
        assert 'service_slug: "space-service"' in extracted

    def test_extract_validates_content(self):
        # Should NOT extract a block if it lacks key fields
        text = """
```yaml
some_random_config: true
but_no_version: true
```
"""
        extracted = TextBlockExtractor.extract_block(text)
        assert extracted is None

    def test_multiple_blocks_selects_valid(self):
        # First block is random code, second is scaffolding
        text = """
Here is some code:
```python
print("hello")
```

And here is the contract:
```scaffolding
version: "1.0"
technology_stack: "java"
service_slug: "real-service"
```
"""
        extracted = TextBlockExtractor.extract_block(text)
        assert extracted is not None
        assert 'technology_stack: "java"' in extracted

    def test_extract_legacy(self):
        text = "--- SCAFFOLDING_CONTRACT:v1 ---\nversion: \"1.0\"\nservice_slug: \"legacy\"\ntechnology_stack: \"legacy\"\n--- /SCAFFOLDING_CONTRACT ---"
        extracted = TextBlockExtractor.extract_block(text)
        assert extracted is not None
        assert 'service_slug: "legacy"' in extracted

