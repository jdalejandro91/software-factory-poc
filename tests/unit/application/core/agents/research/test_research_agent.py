
from unittest.mock import MagicMock

import pytest

from software_factory_poc.application.ports.drivers.research import ResearchAgent
from software_factory_poc.application.core.agents.scaffolding.config.scaffolding_agent_config import \
    ScaffoldingAgentConfig


@pytest.fixture
def mock_gateway():
    return MagicMock()

@pytest.fixture
def mock_config():
    config = MagicMock(spec=ScaffoldingAgentConfig)
    config.architecture_page_id = "12345"
    return config

def test_research_agent_architecture_query(mock_gateway, mock_config):
    agent = ResearchAgent(name="Res", role="Res", goal="Test", gateway=mock_gateway, config=mock_config)
    
    agent.investigate("Please find architecture guidelines")
    
    # Should call get_page_content with configured ID
    mock_gateway.get_page_content.assert_called_once_with("12345")
    mock_gateway.retrieve_context.assert_not_called()

def test_research_agent_general_query(mock_gateway, mock_config):
    agent = ResearchAgent(name="Res", role="Res", goal="Test", gateway=mock_gateway, config=mock_config)
    
    agent.investigate("How to use python")
    
    # Should search
    mock_gateway.retrieve_context.assert_called_once_with("How to use python")
    mock_gateway.get_page_content.assert_not_called()

def test_research_agent_empty_response(mock_gateway, mock_config):
    agent = ResearchAgent(name="Res", role="Res", goal="Test", gateway=mock_gateway, config=mock_config)
    mock_gateway.retrieve_context.return_value = ""
    
    result = agent.investigate("query")
    assert result == "No context found."
