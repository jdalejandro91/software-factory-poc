import sys
from unittest.mock import MagicMock

import pytest

# Mock google.genai before import if possible or patch it
mock_genai = MagicMock()
mock_types = MagicMock()
mock_genai.types = mock_types
# Patch sys.modules to simulate google.genai content
sys.modules["google.genai"] = mock_genai

from software_factory_poc.application.core.domain.entities.llm.llm_request import LlmRequest
from software_factory_poc.application.core.domain.value_objects.generation_config import (
    GenerationConfig,
)
from software_factory_poc.application.core.domain.value_objects.message import Message
from software_factory_poc.application.core.domain.value_objects.message_role import MessageRole
from software_factory_poc.application.core.domain.value_objects.model_id import ModelId
from software_factory_poc.application.core.domain.value_objects.output_format import OutputFormat
from software_factory_poc.application.core.domain.configuration.llm_provider_type import LlmProviderType
from software_factory_poc.infrastructure.providers.llms.gemini.mappers.gemini_request_mapper import (
    GeminiRequestMapper,
)


@pytest.fixture
def mapper():
    return GeminiRequestMapper()

def test_to_kwargs_maps_json_format_to_mime_type(mapper):
    # Reset mock to clear previous calls
    mock_types.GenerateContentConfig.reset_mock()
    
    request = LlmRequest(
        model=ModelId(provider=LlmProviderType.GEMINI, name="gemini-1.5-pro"),
        messages=(Message(role=MessageRole.USER, content="Hello"),),
        generation=GenerationConfig(format=OutputFormat.JSON)
    )
    
    kwargs = mapper.to_kwargs(request)
    
    mock_types.GenerateContentConfig.assert_called()
    call_kwargs = mock_types.GenerateContentConfig.call_args.kwargs
    assert call_kwargs["response_mime_type"] == "application/json"

def test_to_kwargs_maps_text_format_to_text_plain(mapper):
    mock_types.GenerateContentConfig.reset_mock()
    
    request = LlmRequest(
        model=ModelId(provider=LlmProviderType.GEMINI, name="gemini-1.5-pro"),
        messages=(Message(role=MessageRole.USER, content="Hello"),),
        generation=GenerationConfig(format=OutputFormat.TEXT)
    )
    
    kwargs = mapper.to_kwargs(request)
    
    mock_types.GenerateContentConfig.assert_called()
    call_kwargs = mock_types.GenerateContentConfig.call_args.kwargs
    assert call_kwargs["response_mime_type"] == "text/plain"
