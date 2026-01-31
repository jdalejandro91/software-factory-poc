from unittest.mock import MagicMock
from software_factory_poc.infrastructure.providers.vcs.services.gitlab_commit_service import GitLabCommitService
from unittest.mock import MagicMock

from software_factory_poc.infrastructure.providers.vcs.services.gitlab_commit_service import GitLabCommitService


def test_commit_files_force_create_optimization():
    mock_client = MagicMock()
    mock_builder = MagicMock()
    service = GitLabCommitService(mock_client, mock_builder)
    
    files = {"a.txt": "content", "b.txt": "content"}
    
    # Execute with force_create=True
    service.commit_files(1, "main", files, "msg", force_create=True)
    
    # Verify file_exists was NOT called (optimization)
    mock_client.head.assert_not_called()
    
    # Verify payload builder received all "create" actions
    args, _ = mock_builder.build_commit_payload.call_args
    # files_action_map is the 4th argument (check signature/impl if keyword or positional)
    # The implementation calls it with keyword 'files_action_map'
    
    kwargs = mock_builder.build_commit_payload.call_args[1]
    action_map = kwargs['files_action_map']
    
    assert action_map["a.txt"] == "create"
    assert action_map["b.txt"] == "create"

def test_commit_files_smart_checking():
    mock_client = MagicMock()
    mock_builder = MagicMock()
    service = GitLabCommitService(mock_client, mock_builder)
    
    # Mock existence: "exists.txt" exists, "new.txt" 404
    mock_client.head.side_effect = [
        MagicMock(status_code=200), # exists.txt
        MagicMock(status_code=404)  # new.txt
    ]
    
    files = {"exists.txt": "v2", "new.txt": "v1"}
    
    service.commit_files(1, "main", files, "msg", force_create=False)
    
    kwargs = mock_builder.build_commit_payload.call_args[1]
    action_map = kwargs['files_action_map']
    
    assert action_map["exists.txt"] == "update"
    assert action_map["new.txt"] == "create"
