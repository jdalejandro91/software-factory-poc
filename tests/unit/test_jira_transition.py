
import pytest
from unittest.mock import MagicMock
from software_factory_poc.infrastructure.providers.tracker.jira_provider_impl import JiraProviderImpl
from software_factory_poc.application.core.agents.common.exceptions.provider_error import ProviderError

def test_resolve_transition_exact_match():
    mock_client = MagicMock()
    # Mock GET transitions response
    transitions = [
        {"id": "11", "name": "In Progress", "to": {"name": "In Progress"}},
        {"id": "21", "name": "Review", "to": {"name": "In Review"}}
    ]
    mock_client.get.return_value.json.return_value = {"transitions": transitions}
    
    provider = JiraProviderImpl(mock_client, MagicMock())
    
    # Exact match for "Review" (Name match)
    tid = provider._resolve_transition_id("KEY-1", "Review")
    assert tid == "21"

def test_resolve_transition_partial_match():
    mock_client = MagicMock()
    transitions = [
        {"id": "31", "name": "Move to Done", "to": {"name": "Done"}}
    ]
    mock_client.get.return_value.json.return_value = {"transitions": transitions}
    
    provider = JiraProviderImpl(mock_client, MagicMock())
    
    # Partial match "Done" -> matches via "Move to Done" name or 'to' status
    tid = provider._resolve_transition_id("KEY-1", "Done")
    assert tid == "31"

def test_resolve_transition_not_found():
    mock_client = MagicMock()
    mock_client.get.return_value.json.return_value = {"transitions": []}
    
    provider = JiraProviderImpl(mock_client, MagicMock())
    
    with pytest.raises(ProviderError) as exc:
        provider._resolve_transition_id("KEY-1", "Space Travel")
    
    assert "not found" in str(exc.value)
