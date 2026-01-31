from unittest.mock import MagicMock

from software_factory_poc.infrastructure.providers.vcs.services.gitlab_branch_service import GitLabBranchService


def test_gitlab_service_conflict_handling():
    mock_client = MagicMock()
    service = GitLabBranchService(mock_client)
    
    # Simulate 400/409 error
    error = Exception("Conflict")
    error.response = MagicMock(status_code=409)
    mock_client.post.side_effect = error
    
    # Simulate existing branch check
    mock_client.get.return_value.status_code = 200
    mock_client.get.return_value.json.return_value = {"name": "main"}
    
    result = service.create_branch(1, "main")
    
    assert result == {"name": "main"}

def test_gitlab_branch_service_404_handling():
    mock_client = MagicMock()
    service = GitLabBranchService(mock_client)
    
    # Case 1: 404
    mock_response_404 = MagicMock()
    mock_response_404.status_code = 404
    mock_client.get.return_value = mock_response_404
    
    assert service.branch_exists(1, "missing-branch") is False
    
    # Case 2: 200
    mock_response_200 = MagicMock()
    mock_response_200.status_code = 200
    mock_client.get.return_value = mock_response_200
    
    assert service.branch_exists(1, "existing-branch") is True
