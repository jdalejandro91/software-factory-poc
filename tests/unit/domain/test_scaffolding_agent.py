import pytest
from unittest.mock import Mock, MagicMock
from software_factory_poc.application.core.entities.scaffolding_agent import ScaffoldingAgent, MaxRetriesExceededError
from software_factory_poc.application.core.entities.scaffolding.scaffolding_request import ScaffoldingRequest
from software_factory_poc.application.core.interfaces.llm_gateway import LLMGatewayPort, LLMError
from software_factory_poc.application.core.interfaces.knowledge_base import KnowledgeBasePort

@pytest.fixture
def mock_llm_gateway():
    return Mock(spec=LLMGatewayPort)

@pytest.fixture
def mock_knowledge_base():
    kb = MagicMock()
    kb.get_knowledge.return_value = "Use Ports and Adapters."
    return kb

@pytest.fixture
def agent(mock_llm_gateway, mock_knowledge_base):
    return ScaffoldingAgent(llm_gateway=mock_llm_gateway, knowledge_port=mock_knowledge_base, model_priority_list=["fast-model", "smart-model"])

@pytest.fixture
def sample_request():
    return ScaffoldingRequest(
        issue_key="TH-1",
        project_key="TH",
        summary="Test",
        raw_instruction="Create a login API",
        reporter="Dev"
    )

def test_execute_success_first_model(agent, mock_knowledge_base, mock_llm_gateway, sample_request):
    mock_llm_gateway.generate_code.return_value = '{"main.py": "print(\'Success Code\')"}'
    
    result = agent.execute_mission(sample_request)
    
    assert result == {"main.py": "print('Success Code')"}
    mock_llm_gateway.generate_code.assert_called_once_with(pytest.approx(any_str_containing("Use Ports and Adapters")), "fast-model")

def test_execute_fallback_to_second_model(agent, mock_knowledge_base, mock_llm_gateway, sample_request):
    # First call fails, second succeeds
    def side_effect(prompt, model):
        if model == "fast-model":
            raise LLMError("Too dumb")
        return '{"main.py": "print(\'Smart Code\')"}'
    
    mock_llm_gateway.generate_code.side_effect = side_effect
    
    result = agent.execute_mission(sample_request)
    
    assert result == {"main.py": "print('Smart Code')"}
    assert mock_llm_gateway.generate_code.call_count == 2
    
    # Verify calls
    calls = mock_llm_gateway.generate_code.call_args_list
    assert calls[0][0][1] == "fast-model"
    assert calls[1][0][1] == "smart-model"

def test_execute_all_models_fail(agent, mock_knowledge_base, mock_llm_gateway, sample_request):
    mock_llm_gateway.generate_code.side_effect = LLMError("Out of credits")
    
    with pytest.raises(MaxRetriesExceededError):
        agent.execute_mission(sample_request)

# Helper for assert_called_with partial matching
class any_str_containing:
    def __init__(self, substr):
        self.substr = substr
    def __eq__(self, other):
        return isinstance(other, str) and self.substr in other
    def __repr__(self):
        return f"any_str_containing('{self.substr}')"
