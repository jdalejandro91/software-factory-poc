
import pytest
from unittest.mock import MagicMock, patch

from software_factory_poc.infrastructure.providers.tracker.mappers.jira_panel_factory import JiraPanelFactory
from software_factory_poc.application.core.agents.reporter.config.reporter_constants import ReporterMessages
from software_factory_poc.infrastructure.providers.tracker.jira_provider_impl import JiraProviderImpl

def test_panel_factory_success_payload():
    text = f"✅ Éxito: Todo bien. MR: http://gitlab/mr/1"
    payload = JiraPanelFactory.create_payload(text)
    
    body = payload["body"]
    assert body["type"] == "doc"
    # Basic structural check for panel
    assert body["content"][0]["type"] == "panel"
    assert body["content"][0]["attrs"]["panelType"] == "success"

def test_panel_factory_error_payload():
    text = f"❌ Fallo: Algo salió mal: Detalle técnico"
    payload = JiraPanelFactory.create_payload(text)
    
    body = payload["body"]
    assert body["content"][0]["attrs"]["panelType"] == "error"

def test_panel_factory_branch_exists_payload():
    text = f"{ReporterMessages.BRANCH_EXISTS_PREFIX}feature/abc|http://link"
    payload = JiraPanelFactory.create_payload(text)
    
    body = payload["body"]
    assert body["content"][0]["attrs"]["panelType"] == "info"

def test_panel_factory_plain_text():
    text = "Just a normal comment"
    payload = JiraPanelFactory.create_payload(text)
    
    body = payload["body"]
    # Should be paragraph, not panel
    assert body["content"][0]["type"] == "paragraph"

@pytest.fixture
def mock_client():
    return MagicMock()

@pytest.fixture
def mock_settings():
    return MagicMock()

def test_provider_delegates_to_factory(mock_client, mock_settings):
    provider = JiraProviderImpl(mock_client, mock_settings)
    
    with patch("software_factory_poc.infrastructure.providers.tracker.mappers.jira_panel_factory.JiraPanelFactory.create_payload") as mock_create:
        mock_create.return_value = {"body": "mocked"}
        mock_client.post.return_value.json.return_value = {}
        
        provider.add_comment("ISSUE-1", "Some Text")
        
        mock_create.assert_called_once_with("Some Text")
        mock_client.post.assert_called_once()
