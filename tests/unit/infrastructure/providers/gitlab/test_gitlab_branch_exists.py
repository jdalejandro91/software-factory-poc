from unittest.mock import MagicMock

import pytest

from software_factory_poc.infrastructure.providers.vcs.gitlab_provider_impl import (
    GitLabProviderImpl,
)
from software_factory_poc.application.core.domain.exceptions.provider_error import ProviderError


@pytest.fixture
def provider():
    mock_client = MagicMock()
    mock_payload = MagicMock()
    return GitLabProviderImpl(mock_client, mock_payload), mock_client

def test_branch_exists_true(provider):
    impl, mock_client = provider
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_client.get.return_value = mock_response
    
    assert impl.branch_exists(1, "feature/test") is True
    mock_client.get.assert_called_with("api/v4/projects/1/repository/branches/feature%2Ftest")

def test_branch_exists_false(provider):
    impl, mock_client = provider
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_client.get.return_value = mock_response
    
    assert impl.branch_exists(1, "feature/missing") is False

def test_branch_exists_raises_on_error(provider):
    impl, mock_client = provider
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.raise_for_status.side_effect = Exception("Server Error")
    mock_client.get.return_value = mock_response
    
    with pytest.raises(ProviderError) as exc:
        impl.branch_exists(1, "feature/error")
        
    assert "Server Error" in exc.value.message

def test_branch_exists_handles_exception_404(provider):
    # Simulate client raising exception directly for 404 if configured that way
    impl, mock_client = provider
    mock_client.get.side_effect = Exception("404 Not Found")
    
    assert impl.branch_exists(1, "feature/exception") is False
