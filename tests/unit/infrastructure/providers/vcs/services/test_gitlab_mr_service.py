
import pytest
import httpx
from unittest.mock import MagicMock
from software_factory_poc.infrastructure.providers.vcs.services.gitlab_mr_service import GitLabMrService

def test_mr_creation_conflict_recovery():
    mock_client = MagicMock()
    service = GitLabMrService(mock_client)
    
    # 1. Post fails with 409
    error = httpx.HTTPStatusError("Conflict", request=MagicMock(), response=MagicMock(status_code=409))
    mock_client.post.side_effect = error
    
    # 2. Get succeeds and finds MR
    mock_client.get.return_value.status_code = 200
    mock_client.get.return_value.json.return_value = [{"iid": 123, "web_url": "http://mr"}]
    
    result = service.create_merge_request(1, "source", "target", "title")
    
    assert result["iid"] == 123
    assert result["web_url"] == "http://mr"
    
    # Verify Get params
    mock_client.get.assert_called_with(
        "api/v4/projects/1/merge_requests", 
        params={"source_branch": "source", "target_branch": "target", "state": "opened"}
    )
    
def test_mr_creation_conflict_unresolvable():
    mock_client = MagicMock()
    service = GitLabMrService(mock_client)
    
    mock_client.post.side_effect = httpx.HTTPStatusError("Conflict", request=MagicMock(), response=MagicMock(status_code=409))
    mock_client.get.return_value.json.return_value = [] # Empty list
    
    with pytest.raises(ValueError) as exc:
        service.create_merge_request(1, "source", "target", "title")
    
    assert "conflict detected but could not be resolved" in str(exc.value)
