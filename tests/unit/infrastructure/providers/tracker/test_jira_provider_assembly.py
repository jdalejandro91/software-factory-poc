import unittest
from unittest.mock import MagicMock
from software_factory_poc.infrastructure.providers.tracker.jira_provider_impl import JiraProviderImpl
from software_factory_poc.infrastructure.providers.tracker.clients.jira_http_client import JiraHttpClient
from software_factory_poc.infrastructure.configuration.jira_settings import JiraSettings
from software_factory_poc.application.core.domain.entities.task import TaskDescription

class TestJiraProviderAssembly(unittest.TestCase):
    
    def setUp(self):
        self.mock_client = MagicMock(spec=JiraHttpClient)
        self.mock_settings = MagicMock(spec=JiraSettings)
        self.provider = JiraProviderImpl(self.mock_client, self.mock_settings)
        
    def test_update_task_description_format(self):
        # 1. SETUP
        clean_raw_content = "Requerimiento de arquitectura..."
        # Nested config simulation
        config = {
            "version": "1.0", 
            "code_review_params": {
                "gitlab_project_id": 999
            }
        }
        
        description = TaskDescription(
            raw_content=clean_raw_content,
            config=config
        )
        
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 204
        self.mock_client.put.return_value = mock_response
        
        # 2. EXECUTE
        self.provider.update_task_description("TEST-123", description)
        
        # 3. VERIFY
        args, kwargs = self.mock_client.put.call_args
        payload = args[1]
        
        adf_content = payload["fields"]["description"]["content"]
        paragraph = adf_content[0]
        text_node = paragraph["content"][0]
        sent_text = text_node["text"]
        
        print(f"\n[DEBUG] Final Assembled Text:\n{repr(sent_text)}")
        
        # Assertions for "Markdown Output"
        # 1. Start Tag: Expect markdown ```yaml
        self.assertEqual(sent_text.count("```yaml"), 1, "Should have exactly one opening ```yaml block")
        
        # 2. Total Backtick Triplets: Expect 2 (Start + End)
        self.assertEqual(sent_text.count("```"), 2, "Should have exactly two ``` delimiters")
        
        # 3. Content Checks
        self.assertIn("Requerimiento de arquitectura...", sent_text)
        self.assertIn("version: '1.0'", sent_text)
        self.assertIn("code_review_params:", sent_text)
        
        # 4. Indentation Check (YAML nesting)
        # We expect "  gitlab_project_id: 999" (2 spaces indent)
        self.assertIn("  gitlab_project_id: 999", sent_text)
        
        # 5. Order Check
        parts = sent_text.split("\n\n```yaml")
        self.assertEqual(len(parts), 2, "Should be split exactly once by double newline + markdown start")
        self.assertEqual(parts[0].strip(), clean_raw_content)
        self.assertTrue(parts[1].strip().endswith("```"), "Block should end with closing backticks")

if __name__ == "__main__":
    unittest.main()
