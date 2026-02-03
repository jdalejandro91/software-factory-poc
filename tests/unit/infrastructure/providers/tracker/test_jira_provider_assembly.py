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
        
    def test_update_task_description_assembles_yaml_correctly(self):
        # Input Task Description: Pure Text + Config Dict
        desc = TaskDescription(
            raw_content="My Human Description",
            config={
                "scaffolding": {
                     "stack": "python"
                }
            }
        )
        
        # Setup Mock Response
        mock_response = MagicMock()
        mock_response.status_code = 204
        self.mock_client.put.return_value = mock_response
        
        # Execute
        self.provider.update_task_description("TEST-123", desc)
        
        # Verify 
        # Check what arguments were passed to client.put
        args, kwargs = self.mock_client.put.call_args
        endpoint = args[0]
        payload = args[1]
        
        self.assertEqual(endpoint, "rest/api/3/issue/TEST-123")
        
        # The payload structure is intricate (ADF), verifying exact JSON is hard without parsing ADF.
        # But we know our Mapper puts the 'raw_content' into a paragraph.
        # So we check if our assembled string is inside the payload.
        
        adf_content = payload["fields"]["description"]["content"]
        paragraph = adf_content[0]
        text_node = paragraph["content"][0]
        sent_text = text_node["text"]
        
        expected_part_1 = "My Human Description"
        expected_part_2 = "{code:yaml}"
        expected_part_3 = "stack: python"
        
        self.assertIn(expected_part_1, sent_text)
        self.assertIn(expected_part_2, sent_text)
        self.assertIn(expected_part_3, sent_text)
        
        # Verify order: Text -> Newlines -> Code Block
        self.assertTrue(sent_text.startswith("My Human Description\n\n{code:yaml}"))

if __name__ == "__main__":
    unittest.main()
