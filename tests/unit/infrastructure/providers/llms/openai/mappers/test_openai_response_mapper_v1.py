import pytest
from unittest.mock import MagicMock
from software_factory_poc.infrastructure.providers.llms.openai.mappers.openai_response_mapper import OpenAiResponseMapper
from software_factory_poc.application.core.value_objects.provider_name import ProviderName

@pytest.fixture
def mapper():
    return OpenAiResponseMapper()

def test_to_domain_valid_content(mapper):
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "Hello World"
    mock_response.choices = [mock_choice]
    mock_response.model = "gpt-4"
    
    result = mapper.to_domain("gpt-4", mock_response)
    
    assert result.content == "Hello World"
    assert result.model.name == "gpt-4"
    assert result.model.provider == ProviderName.OPENAI

def test_to_domain_strips_markdown_json(mapper):
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "```json\n{\"key\": \"value\"}\n```"
    mock_response.choices = [mock_choice]
    
    result = mapper.to_domain("gpt-4", mock_response)
    
    assert result.content == "{\"key\": \"value\"}"

def test_to_domain_raises_error_on_empty_content(mapper):
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = None
    
    # helper for clean setup
    def setup_reason(reason):
        mock_choice.finish_reason = reason
        mock_response.choices = [mock_choice]
    
    # Test length
    setup_reason("length")
    with pytest.raises(ValueError) as exc:
        mapper.to_domain("gpt-4", mock_response)
    assert "Max tokens exceeded" in str(exc.value)

    # Test content_filter
    setup_reason("content_filter")
    with pytest.raises(ValueError) as exc:
         mapper.to_domain("gpt-4", mock_response)
    assert "content_filter triggered" in str(exc.value)

    # Test unknown
    setup_reason("unknown")
    with pytest.raises(ValueError) as exc:
         mapper.to_domain("gpt-4", mock_response)
    assert "OpenAI returned empty content. Finish reason: unknown" in str(exc.value)

def test_to_domain_raises_error_on_structure_mismatch(mapper):
    # Simulate a response that doesn't follow SDK v1 structure
    mock_response = MagicMock()
    del mock_response.choices 
    
    with pytest.raises(ValueError) as exc:
        mapper.to_domain("gpt-4", mock_response)
        
    assert "Failed to map OpenAI response" in str(exc.value)
