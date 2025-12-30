
import pytest
from unittest.mock import MagicMock
from software_factory_poc.infrastructure.providers.llms.gateway.composite_gateway import CompositeLlmGateway
from software_factory_poc.application.core.domain.configuration.llm_provider_type import LlmProviderType
from software_factory_poc.application.core.domain.value_objects.model_id import ModelId

class TestCompositeGatewayRobustness:
    def test_handles_mixed_priority_list_types(self):
        # Setup
        mock_openai_client = MagicMock()
        mock_openai_client.generate_code.return_value = "OpenAI Code"
        
        mock_anthropic_client = MagicMock()
        mock_anthropic_client.generate_code.return_value = "Anthropic Code"

        clients = {
            LlmProviderType.OPENAI: mock_openai_client,
            LlmProviderType.ANTHROPIC: mock_anthropic_client
        }
        
        config = MagicMock()
        # Mixed list: [ModelId, Dict, Enum, Garbage]
        config.llm_priority_list = [
            # 1. Invalid garbage (Should skip)
            "GarbageString",
            # 2. Dict with invalid provider (Should skip)
            {"provider": "unknown", "name": "foo"},
            # 3. Valid Enum (Should use)
            LlmProviderType.ANTHROPIC, 
            # 4. Valid ModelId (Should NOT reach if above succeeds, but good to have in list)
            ModelId(provider=LlmProviderType.OPENAI, name="gpt-4")
        ]
        
        gateway = CompositeLlmGateway(config, clients)
        
        # ACT
        # Expectation: Garbage skipped -> Unknown skipped -> Anthropic used (as Enum)
        result = gateway.generate_code("prompt", model="default-model")
        
        # ASSERT
        assert result == "Anthropic Code"
        # Since Enum doesn't have name, it falls back to passed 'model' param
        mock_anthropic_client.generate_code.assert_called_with("prompt", model="default-model")

    def test_handles_dict_correctly(self):
        mock_client = MagicMock()
        mock_client.generate_code.return_value = "Code"
        clients = {LlmProviderType.GEMINI: mock_client}
        
        config = MagicMock()
        config.llm_priority_list = [
            {"provider": "gemini", "name": "gemini-pro"}
        ]
        
        gateway = CompositeLlmGateway(config, clients)
        result = gateway.generate_code("prompt", "default")
        
        assert result == "Code"
        mock_client.generate_code.assert_called_with("prompt", model="gemini-pro")
