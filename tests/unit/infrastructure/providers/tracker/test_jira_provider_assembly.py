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
        config = {"version": "1.0", "new_param": "value"}
        
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
        
        # Extract the content sent to Jira
        # The mapper wraps it in a paragraph, let's find the text node.
        # Structure is {"fields": {"description": {"content": [{"content": [{"text": "..."}]}]}}}
        adf_content = payload["fields"]["description"]["content"]
        paragraph = adf_content[0]
        text_node = paragraph["content"][0]
        sent_text = text_node["text"]
        
        print(f"\n[DEBUG] Final Assembled Text: {sent_text}")
        print(f"[DEBUG] Repr: {repr(sent_text)}")
        
        count_yaml_start = sent_text.count("{code:yaml}")
        count_code = sent_text.count("{code}")
        
        print(f"[DEBUG] count({{code:yaml}}) = {count_yaml_start}")
        print(f"[DEBUG] count({{code}}) = {count_code}")
        
        # Assertions for "Perfect Format"
        # 1. Start Tag Count
        self.assertEqual(count_yaml_start, 1, f"Should have exactly one opening code:yaml tag. Found {count_yaml_start}")
        
        # 2. Closing Tag Count
        # Note: "{code:yaml}" does NOT contain "{code}" as a substring (the brace is after yaml).
        # So we expect exactly ONE "{code}" which is the closing tag.
        self.assertEqual(count_code, 1, f"Should have exactly one closing {{code}} tag. Found {count_code}")
        
        # 3. Content Checks
        self.assertIn("Requerimiento de arquitectura...", sent_text)
        self.assertIn("version: '1.0'", sent_text) # yaml dump quotes strings often, check loosely or exacting
        self.assertIn("new_param: value", sent_text)
        
        # 4. Order Check: Text first, then double newline, then code block
        # We can spli and check parts
        parts = sent_text.split("\n\n{code:yaml}")
        self.assertEqual(len(parts), 2, "Should be split exactly once by double newline + code start")
        
        self.assertEqual(parts[0].strip(), clean_raw_content)
        self.assertTrue(parts[1].strip().endswith("{code}"), "Code block should end with closing tag")

if __name__ == "__main__":
    unittest.main()
