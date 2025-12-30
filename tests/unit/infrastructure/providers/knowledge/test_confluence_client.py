
import pytest
from unittest.mock import MagicMock, patch
from software_factory_poc.infrastructure.providers.knowledge.clients.confluence_http_client import ConfluenceHttpClient

class TestConfluenceHttpClient:
    @patch('software_factory_poc.infrastructure.providers.knowledge.clients.confluence_http_client.httpx.Client')
    def test_get_page_calls_correct_endpoint(self, mock_client_cls):
        # Setup
        settings = MagicMock()
        settings.confluence_base_url = "https://wiki.example.com"
        settings.confluence_user_email = "test@example.com"
        settings.confluence_api_token.get_secret_value.return_value = "secret"
        
        client = ConfluenceHttpClient(settings)
        
        mock_get = mock_client_cls.return_value.__enter__.return_value.get
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"id": "123", "title": "Test Page"}

        # Execute
        result = client.get_page("123")

        # Verify
        assert result["id"] == "123"
        mock_get.assert_called_with(
            "https://wiki.example.com/rest/api/content/123",
            auth=("test@example.com", "secret"),
            params={"expand": "body.storage"}
        )

    @patch('software_factory_poc.infrastructure.providers.knowledge.clients.confluence_http_client.httpx.Client')
    def test_search_constructs_cql(self, mock_client_cls):
        # Setup
        settings = MagicMock()
        settings.confluence_base_url = "https://wiki.example.com"
        client = ConfluenceHttpClient(settings)
        
        mock_get = mock_client_cls.return_value.__enter__.return_value.get
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"results": [{"id": "100"}]}

        # Execute
        results = client.search("python architecture")

        # Verify
        assert len(results) == 1
        mock_get.assert_called()
        call_args = mock_get.call_args
        params = call_args.kwargs['params']
        assert params['cql'] == 'text ~ "python architecture"'
        assert params['expand'] == 'body.storage'
