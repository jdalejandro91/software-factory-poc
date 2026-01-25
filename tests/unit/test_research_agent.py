
import pytest
from unittest.mock import MagicMock
from software_factory_poc.application.core.agents.research.research_agent import ResearchAgent
from software_factory_poc.application.core.agents.scaffolding.config.scaffolding_agent_config import ScaffoldingAgentConfig
from software_factory_poc.infrastructure.providers.research.confluence_provider_impl import ConfluenceProviderImpl
from software_factory_poc.infrastructure.configuration.confluence_settings import ConfluenceSettings

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

def test_confluence_html_cleaning():
    settings = MagicMock()
    settings.base_url = "http://confluence.com"
    settings.user_email = "test@example.com"
    settings.api_token.get_secret_value.return_value = "token"
    provider = ConfluenceProviderImpl(settings)
    
    dirty_html = "<p>Clean <b>Text</b> &amp; More</p>"
    clean = provider._sanitize_content(dirty_html)
    
    assert "Clean Text & More" in clean
    assert "<p>" not in clean
    assert "&amp;" not in clean

def test_research_agent_empty_response(mock_gateway, mock_config):
    agent = ResearchAgent(name="Res", role="Res", goal="Test", gateway=mock_gateway, config=mock_config)
    mock_gateway.retrieve_context.return_value = ""
    
    result = agent.investigate("query")
    assert result == "No context found."
