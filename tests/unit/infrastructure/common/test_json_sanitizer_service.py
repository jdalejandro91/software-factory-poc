import pytest
from pydantic import BaseModel
from src.software_factory_poc.infrastructure.common.json_sanitizer_service import (
    JsonParsingError,
    JsonSanitizerService,
    SchemaValidationError,
)


# Test Data Model
class SampleModel(BaseModel):
    key: str
    value: int

def test_extract_clean_json_successful():
    raw = '{"key": "test", "value": 123}'
    obj = JsonSanitizerService.extract_and_validate_json(raw, SampleModel)
    assert obj.key == "test"
    assert obj.value == 123

def test_extract_markdown_wrapped_json():
    raw = """
    Here is the data:
    ```json
    {
        "key": "embedded",
        "value": 456
    }
    ```
    Hope it helps!
    """
    obj = JsonSanitizerService.extract_and_validate_json(raw, SampleModel)
    assert obj.key == "embedded"
    assert obj.value == 456

def test_extract_dirty_text_surrounding():
    raw = "Sure, { \"key\": \"dirty\", \"value\": 789 } text after."
    obj = JsonSanitizerService.extract_and_validate_json(raw, SampleModel)
    assert obj.key == "dirty"
    assert obj.value == 789

def test_validation_error_structure():
    raw = '{"key": "test", "value": "not-an-number"}'
    with pytest.raises(SchemaValidationError) as exc:
        JsonSanitizerService.extract_and_validate_json(raw, SampleModel)
    assert "JSON Structure Invalid" in str(exc.value)

def test_parsing_error_malformed_json():
    raw = '{"key": "test", "value": 123' # Missing brace
    with pytest.raises(JsonParsingError):
         # Logic: Regex catches '{... 123', assuming it matches nothing? 
         # Or it attempts fallback. Fallback returns same. 
         # Pydantic fails to parse.
         JsonSanitizerService.extract_and_validate_json(raw, SampleModel)

def test_parsing_error_no_braces():
    raw = "No json here"
    with pytest.raises(JsonParsingError):
        JsonSanitizerService.extract_and_validate_json(raw, SampleModel)
