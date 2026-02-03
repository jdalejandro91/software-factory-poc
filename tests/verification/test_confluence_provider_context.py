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
        # 1. Setup Empty Result for Root AND Direct (Fallback)
        self.provider.http_client.search.return_value = []

        # 2. Execute & Assert
        with self.assertRaises(ProviderError) as cm:
            self.provider.get_project_context("unknown")
        
        # New robust error message
        self.assertIn("Project folder 'unknown' NOT FOUND", str(cm.exception))

    def test_get_project_context_project_not_found(self):
        # 1. Setup Root Found but Project Not Found, AND Direct Search Not Found
        self.provider.http_client.search.side_effect = [
            [{"id": "root-123", "title": "Projects"}], # Root -> Found
            [], # Project under Root -> Not Found
            []  # Direct Search (Fallback) -> Not Found
        ]

        # 2. Execute & Assert
        with self.assertRaises(ProviderError) as cm:
            self.provider.get_project_context("new-service")
        
        self.assertIn("Project folder 'new-service' NOT FOUND", str(cm.exception))

    def test_fallback_strategy_fetches_children(self):
        # 1. Setup Failure for Root Finding (Hierarchical Search fails)
        # First call returns [], causing fall through to direct search
        # 2. Setup Success for Direct Search
        # Second call returns the project folder directly
        self.provider.http_client.search.side_effect = [
            [], # Root Query -> Empty
            [{"id": "999", "title": "shopping-cart"}] # Direct Query -> Found
        ]
        
        # 3. Setup Children Fetch
        self.provider.http_client.get_child_pages.return_value = [
            {
                "id": "doc-A", 
                "title": "Doc A", 
                "body": {"storage": {"value": "<p>Content A is sufficiently long to pass the 50 characters validation threshold required by the extractor.</p>"}}, 
                "_links": {"webui": "/doc/A"},
                "space": {"key": "DDS"}
            },
            {
                "id": "doc-B", 
                "title": "Doc B", 
                "body": {"storage": {"value": "<p>Content B is also sufficiently long to pass the 50 characters validation threshold required by the extractor.</p>"}}, 
                "_links": {"webui": "/doc/B"},
                "space": {"key": "DDS"}
            }
        ]

        # 4. Execute
        ctx = self.provider.get_project_context("shopping-cart")

        # 5. Verify
        # Check call sequence
        call_args_list = self.provider.http_client.search.call_args_list
        self.assertEqual(len(call_args_list), 2)
        # First query was root
        self.assertIn('title in ("projects", "Projects")', call_args_list[0][0][0])
        # Second query was direct (Fuzzy)
        self.assertIn('space = "DDS" AND type = "page" AND title ~ "shopping-cart"', call_args_list[1][0][0])
        
        # Check Context Populated
        self.assertEqual(ctx.project_name, "shopping-cart")
        self.assertEqual(ctx.root_page_id, "999")
        self.assertEqual(len(ctx.documents), 2)
        self.assertEqual(ctx.documents[0].title, "Doc A")

    def test_fuzzy_search_resolves_folder_and_children(self):
        # 1. Setup Failure for Root
        # 2. Setup Success for Fuzzy Search (returns noise + correct match)
        self.provider.http_client.search.side_effect = [
            [], # Root -> Empty
            [
                {"id": "888", "title": "Start Shopping Cart Now"}, # Noise
                {"id": "999", "title": "Shopping Cart"} # Exact Match (after normalization)
            ] 
        ]
        
        # 3. Setup Children
        self.provider.http_client.get_child_pages.return_value = [
            {"id": "d1", "title": "T1", "body": "...", "_links": {}, "space": {}}
        ]

        # 4. Execute
        ctx = self.provider.get_project_context("shopping-cart")

        # 5. Verify
        self.assertEqual(ctx.root_page_id, "999") # Should pick the exact match
        self.assertEqual(len(ctx.documents), 1)
        
        # Check fuzzy query syntax
        call_args = self.provider.http_client.search.call_args_list[1]
        self.assertIn('title ~ "shopping-cart"', call_args[0][0])

    def test_project_not_found_even_with_fallback(self):
        # 1. Setup Failure for ALL Searches
        self.provider.http_client.search.side_effect = [
            [], # Root Query -> Empty
            []  # Direct Query -> Empty
        ]

        # 2. Execute & Assert
        with self.assertRaises(ProviderError) as cm:
            self.provider.get_project_context("phantom-project")
        
        self.assertIn("NOT FOUND (searched hierarchically & directly", str(cm.exception))

if __name__ == "__main__":
    unittest.main()
