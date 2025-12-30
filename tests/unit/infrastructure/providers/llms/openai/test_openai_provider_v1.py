from unittest.mock import AsyncMock, MagicMock

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
from software_factory_poc.infrastructure.common.retry.retry_policy import RetryPolicy
from software_factory_poc.infrastructure.observability.logging.correlation_id_context import (
    CorrelationIdContext,
)
from software_factory_poc.infrastructure.providers.llms.openai.mappers.openai_request_mapper import (
    OpenAiRequestMapper,
)
from software_factory_poc.infrastructure.providers.llms.openai.mappers.openai_response_mapper import (
    OpenAiResponseMapper,
)
from software_factory_poc.infrastructure.providers.llms.openai.openai_provider_impl import (
    OpenAiProvider,
)


@pytest.mark.asyncio
async def test_call_uses_chat_completions_create_with_json_mode():
    # Arrange
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value="mock_response")
    
    mock_request_mapper = MagicMock(spec=OpenAiRequestMapper)
    mock_request_mapper.to_kwargs.return_value = {"model": "gpt-4", "messages": []}
    
    mock_response_mapper = MagicMock(spec=OpenAiResponseMapper)
    mock_response_mapper.to_domain.return_value = "domain_response"
    
    provider = OpenAiProvider(
        client=mock_client,
        retry=MagicMock(spec=RetryPolicy),
        request_mapper=mock_request_mapper,
        response_mapper=mock_response_mapper,
        correlation=MagicMock(spec=CorrelationIdContext)
    )
    
    # Request with json_mode=True
    request = LlmRequest(
        model=ModelId(provider=LlmProviderType.OPENAI, name="gpt-4"),
        messages=(Message(role=MessageRole.USER, content="hello"),),
        generation=GenerationConfig(format=OutputFormat.JSON)
    )
    
    # Act
    await provider._call(request)
    
    # Assert
    mock_client.chat.completions.create.assert_called_once()
    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    
    assert call_kwargs["response_format"] == {"type": "json_object"}
    assert call_kwargs["model"] == "gpt-4"

@pytest.mark.asyncio
async def test_call_uses_chat_completions_create_without_json_mode():
    # Arrange
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value="mock_response")
    
    mock_request_mapper = MagicMock(spec=OpenAiRequestMapper)
    mock_request_mapper.to_kwargs.return_value = {"model": "gpt-4", "messages": []}
    
    mock_response_mapper = MagicMock(spec=OpenAiResponseMapper)
    
    provider = OpenAiProvider(
        client=mock_client,
        retry=MagicMock(spec=RetryPolicy),
        request_mapper=mock_request_mapper,
        response_mapper=mock_response_mapper,
        correlation=MagicMock(spec=CorrelationIdContext)
    )
    
    # Request with json_mode=False
    request = LlmRequest(
        model=ModelId(provider=LlmProviderType.OPENAI, name="gpt-4"),
        messages=(Message(role=MessageRole.USER, content="hello"),),
        generation=GenerationConfig(format=OutputFormat.TEXT)
    )
    
    # Act
    await provider._call(request)
    
    # Assert
    mock_client.chat.completions.create.assert_called_once()
    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    
    assert "response_format" not in call_kwargs
    assert call_kwargs["model"] == "gpt-4"
