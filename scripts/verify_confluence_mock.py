
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.append(str(Path.cwd() / "src"))

from pydantic import SecretStr

from software_factory_poc.configuration.main_settings import Settings
from software_factory_poc.integrations.confluence.confluence_client import ConfluenceClient
from software_factory_poc.knowledge.architecture_knowledge_service import (
    ArchitectureKnowledgeService,
)


class TestConfluenceIntegration(unittest.TestCase):
    def setUp(self):
        self.settings = Settings(
            jira_webhook_secret=SecretStr("dummy"),
            jira_base_url="https://dummy.atlassian.net",
            openai_api_key=SecretStr("sk-dummy"),
            confluence_base_url="https://confluence.example.com",
            confluence_user_email="user@example.com",
            confluence_api_token=SecretStr("token"),
            architecture_doc_page_id="123456"
        )
        self.html_response = {
            "body": {
                "storage": {
                    "value": "<p>This is <strong>bold</strong> text.</p><p>New line.</p>"
                }
            }
        }

    @patch("httpx.Client")
    def test_client_parsing(self, mock_client_cls):
        # Setup mock
        mock_instance = mock_client_cls.return_value.__enter__.return_value
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.html_response
        mock_instance.get.return_value = mock_response

        # Test Client
        client = ConfluenceClient(self.settings)
        content = client.get_page_content("123456")
        
        print(f"Parsed Content: {repr(content)}")
        
        # Verify cleaning
        # BS4 with \n separator puts newlines around tags
        self.assertIn("This is \nbold\n text.", content)
        self.assertIn("New line.", content)
        self.assertNotIn("<p>", content)

    @patch("httpx.Client")
    def test_service_caching(self, mock_client_cls):
        # Setup mock
        mock_instance = mock_client_cls.return_value.__enter__.return_value
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.html_response
        mock_instance.get.return_value = mock_response
        
        # Test Service
        client = ConfluenceClient(self.settings)
        service = ArchitectureKnowledgeService(client, self.settings)
        
        # First call
        result1 = service.get_architecture_guidelines()
        
        # Second call (should be cached)
        result2 = service.get_architecture_guidelines()
        
        self.assertEqual(result1, result2)
        
        # Verify httpx called only once
        self.assertEqual(mock_instance.get.call_count, 1)
        print("Caching verified: API called once for two requests.")

if __name__ == "__main__":
    unittest.main()
