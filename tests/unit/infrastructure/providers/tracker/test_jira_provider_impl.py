from unittest.mock import MagicMock, patch

import pytest

from software_factory_poc.application.ports.drivers.common.exceptions import ProviderError
from software_factory_poc.infrastructure.adapters.drivers.tracker.jira_provider_impl import JiraProviderImpl


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

def test_get_task_mapping_success(mock_client, mock_settings):
    # Mock Issue Response
    mock_response = {
        "key": "KEY-1",
        "fields": {
             "summary": "Implement Login",
             "status": {"name": "To Do"},
             "project": {"key": "POC", "id": "100"},
             "description": {
                 "type": "doc", 
                 "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Details"}]}]
             }
        }
    }
    
    mock_client.get.return_value.json.return_value = mock_response
    
    provider = JiraProviderImpl(mock_client, mock_settings)
    
    # Execution
    task = provider.get_task("KEY-1")
    
    # Verification
    assert task.key == "KEY-1"
    assert task.summary == "Implement Login"
    assert task.status == "To Do"
    assert task.project_key == "POC" # This line verifies the mapping fix
    assert task.description is not None

