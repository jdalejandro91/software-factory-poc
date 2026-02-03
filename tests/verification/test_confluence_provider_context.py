import unittest
from unittest.mock import MagicMock
from software_factory_poc.infrastructure.providers.research.confluence_provider_impl import ConfluenceProviderImpl
from software_factory_poc.infrastructure.configuration.confluence_settings import ConfluenceSettings
from software_factory_poc.application.core.agents.common.exceptions.provider_error import ProviderError

class TestConfluenceProviderContext(unittest.TestCase):

    def setUp(self):
        self.mock_settings = MagicMock(spec=ConfluenceSettings)
        self.mock_settings.base_url = "https://confluence.example.com"
        mock_secret = MagicMock()
        mock_secret.get_secret_value.return_value = "dummy_token"
        self.mock_settings.api_token = mock_secret
        self.mock_settings.user_email = "test@example.com"
        
        # Mock HttpClient
        self.provider = ConfluenceProviderImpl(self.mock_settings)
        self.provider.http_client = MagicMock()
        # Force space key for consistency
        self.provider.space_key = "DDS"

    def test_get_project_context_success(self):
        # 1. Setup Success for Root Finding
        self.provider.http_client.search.side_effect = [
            [{"id": "root-123", "title": "Projects"}], # Root
            [{"id": "proj-456", "title": "shopping-cart"}] # Project
        ]
        
        # 2. Setup Children Fetch
        self.provider.http_client.get_child_pages.return_value = [
            {
                "id": "doc-1", 
                "title": "Architecture", 
                "body": {"storage": {"value": "<p>Content 1 is sufficiently long to pass the 50 characters validation threshold required by the extractor.</p>"}}, 
                "_links": {"webui": "/doc/1"},
                "space": {"key": "DDS"}
            },
            {
                "id": "doc-2", 
                "title": "API", 
                "body": {"storage": {"value": "<p>Content 2 is also sufficiently long to pass the 50 characters validation threshold required by the extractor.</p>"}}, 
                "_links": {"webui": "/doc/2"},
                "space": {"key": "DDS"}
            }
        ]

        # 3. Execute
        ctx = self.provider.get_project_context("shopping-cart")

        # 4. Verify
        # Check Root Query
        call_args_list = self.provider.http_client.search.call_args_list
        # Root query
        self.assertIn('space = "DDS" AND type = "page" AND title in ("projects", "Projects")', call_args_list[0][0][0])
        # Project Query
        self.assertIn('parent = root-123 AND type = "page" AND title = "shopping-cart"', call_args_list[1][0][0])
        
        self.assertEqual(ctx.project_name, "shopping-cart")
        self.assertEqual(ctx.root_page_id, "proj-456")
        self.assertEqual(len(ctx.documents), 2)
        self.assertIn("Content 1 is sufficiently long", ctx.documents[0].content)

    def test_get_project_context_root_not_found(self):
        # 1. Setup Empty Result for Root
        self.provider.http_client.search.return_value = []

        # 2. Execute & Assert
        with self.assertRaises(ProviderError) as cm:
            self.provider.get_project_context("unknown")
        
        self.assertIn("Root folder 'projects' not found", str(cm.exception))

    def test_get_project_context_project_not_found(self):
        # 1. Setup Root Found but Project Not Found
        self.provider.http_client.search.side_effect = [
            [{"id": "root-123", "title": "Projects"}],
            [] # Project Not Found
        ]

        # 2. Execute
        ctx = self.provider.get_project_context("new-service")

        # 3. Verify Empty Context
        self.assertEqual(ctx.project_name, "new-service")
        self.assertEqual(ctx.root_page_id, "N/A")
        self.assertEqual(len(ctx.documents), 0)

if __name__ == "__main__":
    unittest.main()
