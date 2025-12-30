
import pytest

from software_factory_poc.application.core.domain.entities.llm.llm_request import LlmRequest
from software_factory_poc.application.core.domain.value_objects.generation_config import (
    GenerationConfig,
)
from software_factory_poc.application.core.domain.value_objects.message import Message
from software_factory_poc.application.core.domain.value_objects.message_role import MessageRole
from software_factory_poc.application.core.domain.value_objects.model_id import ModelId
from software_factory_poc.application.core.domain.value_objects.output_format import OutputFormat
from software_factory_poc.application.core.domain.configuration.llm_provider_type import LlmProviderType
from software_factory_poc.infrastructure.providers.llms.openai.mappers.openai_request_mapper import (
    OpenAiRequestMapper,
)


@pytest.fixture
def mapper():
    return OpenAiRequestMapper()

def test_to_kwargs_injects_json_instruction_if_missing(mapper):
    request = LlmRequest(
        model=ModelId(provider=LlmProviderType.OPENAI, name="gpt-4"),
        messages=(Message(role=MessageRole.USER, content="Hello world"),),
        generation=GenerationConfig(format=OutputFormat.JSON)
    )
    
    kwargs = mapper.to_kwargs(request)
    
    assert kwargs["response_format"] == {"type": "json_object"}
    messages = kwargs["messages"]
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert "IMPORTANT: Output valid JSON." in messages[0]["content"]
    assert messages[1]["content"] == "Hello world"

def test_to_kwargs_does_not_inject_if_json_keyword_present(mapper):
    request = LlmRequest(
        model=ModelId(provider=LlmProviderType.OPENAI, name="gpt-4"),
        messages=(Message(role=MessageRole.USER, content="Please output JSON format"),),
        generation=GenerationConfig(format=OutputFormat.JSON)
    )
    
    kwargs = mapper.to_kwargs(request)
    
    assert kwargs["response_format"] == {"type": "json_object"}
    messages = kwargs["messages"]
    assert len(messages) == 1
    assert messages[0]["content"] == "Please output JSON format"

def test_to_kwargs_text_format_no_response_format(mapper):
    request = LlmRequest(
        model=ModelId(provider=LlmProviderType.OPENAI, name="gpt-4"),
        messages=(Message(role=MessageRole.USER, content="Hello"),),
        generation=GenerationConfig(format=OutputFormat.TEXT)
    )
    
    kwargs = mapper.to_kwargs(request)
    
    assert "response_format" not in kwargs
    # Should not inject system message for TEXT format even if "json" is missing
    messages = kwargs["messages"]
    assert len(messages) == 1
    assert messages[0]["role"] == "user"
