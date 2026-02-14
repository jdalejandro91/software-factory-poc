
import pytest

from software_factory_poc.application.ports.drivers.common.exceptions import ContractParseError
from software_factory_poc.application.core.agents.scaffolding.tools.artifact_parser import ArtifactParser


def test_parse_valid_json_with_markdown():
    parser = ArtifactParser()
    raw_text = """
    Here is the code:
    ```json
    [
        {"path": "README.md", "content": "# Hello"},
        {"path": "src/main.py", "content": "print('World')"}
    ]
    ```
    """
    result = parser.parse_response(raw_text)
    assert len(result) == 2
    assert result[0].path == "README.md"
    assert result[0].content == "# Hello"

def test_parse_invalid_json_throws_custom_error():
    parser = ArtifactParser()
    raw_text = "{ invalid json }"
    
    with pytest.raises(ContractParseError) as exc_info:
        parser.parse_response(raw_text)
    
    assert "Invalid JSON format" in str(exc_info.value)
    assert "Snippet: { invalid json }" in str(exc_info.value)

def test_parse_unsafe_paths_are_skipped():
    parser = ArtifactParser()
    raw_text = """
    [
        {"path": "/etc/passwd", "content": "hack"},
        {"path": "../secret.txt", "content": "hack"},
        {"path": "src/valid.py", "content": "ok"}
    ]
    """
    result = parser.parse_response(raw_text)
    assert len(result) == 1
    assert result[0].path == "src/valid.py"

def test_parse_non_list_root():
    parser = ArtifactParser()
    raw_text = '{"path": "foo"}'
    
    with pytest.raises(ContractParseError) as exc_info:
        parser.parse_response(raw_text)
    
    assert "Response must be a list" in str(exc_info.value)
