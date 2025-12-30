
import pytest
from unittest.mock import MagicMock
from software_factory_poc.infrastructure.providers.vcs.gitlab_provider_impl import GitLabProviderImpl

class TestGitLabPathSanitization:
    def test_sanitizes_full_url(self):
        # Setup
        mock_client = MagicMock()
        mock_payload = MagicMock()
        provider = GitLabProviderImpl(mock_client, mock_payload)
        
        # Mock successful response
        mock_client.get.return_value.status_code = 200
        mock_client.get.return_value.json.return_value = {"id": 999}
        
        # Execute with FULL URL
        result_id = provider.resolve_project_id("https://gitlab.com/test-group/test-project")
        
        # Verification
        assert result_id == 999
        # Ensure client called with PATH only ("test-group/test-project" encoded)
        # encoded "test-group/test-project" -> "test-group%2Ftest-project"
        mock_client.get.assert_called_with("api/v4/projects/test-group%2Ftest-project")

    def test_sanitizes_full_url_with_git_extension(self):
        # Setup
        mock_client = MagicMock()
        mock_payload = MagicMock()
        provider = GitLabProviderImpl(mock_client, mock_payload)
        
        mock_client.get.return_value.status_code = 200
        mock_client.get.return_value.json.return_value = {"id": 888}
        
        # Execute
        provider.resolve_project_id("https://gitlab.example.com/foo/bar.git")
        
        # Ensure client called with PATH only ("foo/bar")
        mock_client.get.assert_called_with("api/v4/projects/foo%2Fbar")

    def test_passes_through_simple_path(self):
        # Setup
        mock_client = MagicMock()
        mock_payload = MagicMock()
        provider = GitLabProviderImpl(mock_client, mock_payload)
        
        mock_client.get.return_value.status_code = 200
        mock_client.get.return_value.json.return_value = {"id": 777}
        
        # Execute
        provider.resolve_project_id("foo/bar")
        
        # Ensure client called
        mock_client.get.assert_called_with("api/v4/projects/foo%2Fbar")
