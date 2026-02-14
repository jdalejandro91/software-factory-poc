
from unittest.mock import MagicMock, AsyncMock

import pytest

from software_factory_poc.application.ports.drivers.common.config.llm_provider_type import LlmProviderType
from software_factory_poc.application.ports.drivers.common.value_objects.model_id import ModelId
from software_factory_poc.application.ports.drivers.reasoner.exceptions.all_models_exhausted_error import \
    AllModelsExhaustedException
from software_factory_poc.application.ports.drivers.reasoner import LlmResponse
from software_factory_poc.application.ports.drivers.reasoner.ports.llm_gateway import LLMError
from software_factory_poc.application.core.agents.scaffolding.config.scaffolding_agent_config import \
    ScaffoldingAgentConfig
from software_factory_poc.infrastructure.adapters.drivers.llms.gateway.composite_gateway import CompositeLlmGateway


@pytest.fixture
def mock_config():
    config = MagicMock(spec=ScaffoldingAgentConfig)
    config.llm_model_priority = [
        ModelId(provider=LlmProviderType.OPENAI, name="gpt-4"),
        ModelId(provider=LlmProviderType.ANTHROPIC, name="claude-3")
    ]
    return config

@pytest.fixture
def mock_clients():
    return {
        LlmProviderType.OPENAI: MagicMock(),
        LlmProviderType.ANTHROPIC: MagicMock()
    }

def test_gateway_fallback_success(mock_config, mock_clients):
    gateway = CompositeLlmGateway(mock_config, mock_clients)
    
    # Provider 1 (OpenAI) fails
    mock_clients[LlmProviderType.OPENAI].generate = AsyncMock(side_effect=LLMError("OpenAI Down"))
    
    # Provider 2 (Anthropic) succeeds
    expected_response = LlmResponse(
        model=ModelId(LlmProviderType.ANTHROPIC, "claude-3"), 
        content="Success"
    )
    mock_clients[LlmProviderType.ANTHROPIC].generate = AsyncMock(return_value=expected_response)
    
    result = gateway.generate_code("prompt", "context", [])
    
    assert result.content == "Success"
    assert mock_clients[LlmProviderType.OPENAI].generate.call_count == 1
    assert mock_clients[LlmProviderType.ANTHROPIC].generate.call_count == 1

def test_gateway_exhaustion(mock_config, mock_clients):
    gateway = CompositeLlmGateway(mock_config, mock_clients)
    
    # Both fail
    mock_clients[LlmProviderType.OPENAI].generate = AsyncMock(side_effect=LLMError("Fail 1"))
    mock_clients[LlmProviderType.ANTHROPIC].generate = AsyncMock(side_effect=Exception("Fail 2"))
    
    with pytest.raises(AllModelsExhaustedException):
        gateway.generate_code("prompt", "context", [])
