import unittest
from unittest.mock import MagicMock
from software_factory_poc.infrastructure.adapters.drivers.tracker.jira_provider_impl import JiraProviderImpl
from software_factory_poc.infrastructure.adapters.drivers.tracker.clients import JiraHttpClient
from software_factory_poc.infrastructure.configuration.jira_settings import JiraSettings
from software_factory_poc.domain.entities.task import TaskDescription

class TestJiraProviderDefensiveCleaning(unittest.TestCase):
    
    def setUp(self):
        self.mock_client = MagicMock(spec=JiraHttpClient)
        self.mock_settings = MagicMock(spec=JiraSettings)
        # Using a proper instance to test the logic
        self.provider = JiraProviderImpl(self.mock_client, self.mock_settings)
        
    def test_update_strips_rogue_code_blocks(self):
        # 1. SETUP: Dirty Input
        # raw_content has a lingering block that shouldn't be there
        dirty_raw_content = """My Requirements.
{code:yaml}
old_config: true
{code}
End of requirements."""

        desc = TaskDescription(
            raw_content=dirty_raw_content,
            config={"new_config": True}
        )
        
        # Mock Response
        mock_response = MagicMock()
        mock_response.status_code = 204
        self.mock_client.put.return_value = mock_response
        
        # 2. EXECUTE
        self.provider.update_task_description("TEST-999", desc)
        
        # 3. VERIFY
        args, kwargs = self.mock_client.put.call_args
        payload = args[1]
        
        # Extract the content sent to Jira
        # The mapper wraps it in a paragraph, let's find the text node
        adf_content = payload["fields"]["description"]["content"]
        paragraph = adf_content[0]
        text_node = paragraph["content"][0]
        sent_text = text_node["text"]
        
        print(f"\n[DEBUG] Sent Text:\n{sent_text}")
        
        # Assertions
        # 1. The rogue block should be GONE
        self.assertNotIn("old_config: true", sent_text)
        
        # 2. The NEW block should be present
        self.assertIn("new_config: true", sent_text)
        
        # 3. There should be EXACTLY ONE code block
        self.assertEqual(sent_text.count("{code:yaml}"), 1)
        self.assertEqual(sent_text.count("{code}"), 1) # Closing tag
        
        # 4. Text around it should persist
        self.assertIn("My Requirements.", sent_text)
        self.assertIn("End of requirements.", sent_text)

if __name__ == "__main__":
    unittest.main()
