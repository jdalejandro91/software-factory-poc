import pytest
from unittest.mock import MagicMock, patch
from software_factory_poc.infrastructure.providers.tracker.jira_provider_impl import JiraProviderImpl
from software_factory_poc.infrastructure.providers.tracker.mappers.jira_panel_factory import JiraPanelFactory
from software_factory_poc.application.core.agents.common.exceptions.provider_error import ProviderError

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

def test_resolve_transition_exact_match(mock_client, mock_settings):
    # Mock GET transitions response
    transitions = [
        {"id": "11", "name": "In Progress", "to": {"name": "In Progress"}},
        {"id": "21", "name": "Review", "to": {"name": "In Review"}}
    ]
    mock_client.get.return_value.json.return_value = {"transitions": transitions}
    
    provider = JiraProviderImpl(mock_client, mock_settings)
    
    # Exact match for "Review" (Name match)
    tid = provider._resolve_transition_id("KEY-1", "Review")
    assert tid == "21"

def test_resolve_transition_partial_match(mock_client, mock_settings):
    transitions = [
        {"id": "31", "name": "Move to Done", "to": {"name": "Done"}}
    ]
    mock_client.get.return_value.json.return_value = {"transitions": transitions}
    
    provider = JiraProviderImpl(mock_client, mock_settings)
    
    # Partial match "Done" -> matches via "Move to Done" name or 'to' status
    tid = provider._resolve_transition_id("KEY-1", "Done")
    assert tid == "31"

def test_resolve_transition_not_found(mock_client, mock_settings):
    mock_client.get.return_value.json.return_value = {"transitions": []}
    
    provider = JiraProviderImpl(mock_client, mock_settings)
    
    with pytest.raises(ProviderError) as exc:
        provider._resolve_transition_id("KEY-1", "Space Travel")
    
    assert "not found" in str(exc.value)
