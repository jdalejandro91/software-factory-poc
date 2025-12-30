
import pytest
from unittest.mock import MagicMock
from software_factory_poc.infrastructure.providers.llms.gateway.composite_gateway import CompositeLlmGateway
from software_factory_poc.application.core.domain.value_objects.model_id import ModelId
from software_factory_poc.application.core.domain.configuration.llm_provider_type import LlmProviderType
from software_factory_poc.application.core.domain.exceptions.all_models_exhausted_error import AllModelsExhaustedException

class TestCompositeGatewayLogic:
    def test_uses_correct_model_name_from_priority_list(self):
        # Setup
        mock_config = MagicMock()
        # Priority list contains ModelId objects, NOT just Enums
        model_1 = ModelId(provider=LlmProviderType.OPENAI, name="gpt-4-custom")
        model_2 = ModelId(provider=LlmProviderType.DEEPSEEK, name="deepseek-coder")
        mock_config.llm_model_priority = [model_1, model_2]

        mock_openai_client = MagicMock()
        mock_deepseek_client = MagicMock()
        
        clients = {
            LlmProviderType.OPENAI: mock_openai_client,
            LlmProviderType.DEEPSEEK: mock_deepseek_client
        }

        gateway = CompositeLlmGateway(mock_config, clients)
        
        # Scenario: OpenAI works
        mock_openai_client.generate_code.return_value = "code_v1"
        
        result = gateway.generate_code("prompt", model="ignored")
        
        assert result == "code_v1"
        # Verify it used the NAME from ModelId ("gpt-4-custom"), not "ignored"
        mock_openai_client.generate_code.assert_called_with("prompt", model="gpt-4-custom")

    def test_falls_back_to_next_on_error(self):
        mock_config = MagicMock()
        model_1 = ModelId(provider=LlmProviderType.OPENAI, name="gpt-4-fail")
        model_2 = ModelId(provider=LlmProviderType.DEEPSEEK, name="deepseek-success")
        mock_config.llm_model_priority = [model_1, model_2]

        mock_openai = MagicMock()
        mock_deepseek = MagicMock()
        
        clients = {LlmProviderType.OPENAI: mock_openai, LlmProviderType.DEEPSEEK: mock_deepseek}
        
        gateway = CompositeLlmGateway(mock_config, clients)
        
        # OpenAI fails
        mock_openai.generate_code.side_effect = Exception("Boom")
        # Deepseek success
        mock_deepseek.generate_code.return_value = "code_v2"
        
        result = gateway.generate_code("prompt", "ignored")
        
        assert result == "code_v2"
        mock_deepseek.generate_code.assert_called_with("prompt", model="deepseek-success")
