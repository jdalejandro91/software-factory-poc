import unittest
from unittest.mock import MagicMock
from software_factory_poc.infrastructure.adapters.drivers.tracker.jira_provider_impl import JiraProviderImpl
from software_factory_poc.infrastructure.adapters.drivers.tracker.clients import JiraHttpClient
from software_factory_poc.infrastructure.configuration.jira_settings import JiraSettings
from software_factory_poc.application.core.domain.entities.task import TaskDescription

class TestJiraProviderAssembly(unittest.TestCase):
    
    def setUp(self):
        self.mock_client = MagicMock(spec=JiraHttpClient)
        self.mock_settings = MagicMock(spec=JiraSettings)
        self.provider = JiraProviderImpl(self.mock_client, self.mock_settings)
        
    def test_update_task_description_generates_native_adf(self):
        # 1. SETUP
        clean_raw_content = "Requerimiento de arquitectura..."
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
        
        # Structure check: {"fields": {"description": {"content": [...], "type": "doc", "version": 1}}}
        adf = payload["fields"]["description"]
        self.assertEqual(adf["type"], "doc")
        self.assertEqual(adf["version"], 1)
        
        content_nodes = adf["content"]
        # Expecting: 
        # 1. Paragraph (Text)
        # 2. Paragraph (Spacer - optional depending on impl, but mapper calls create_paragraph([]))
        # 3. CodeBlock (YAML)
        
        # Let's inspect the nodes types
        node_types = [n["type"] for n in content_nodes]
        print(f"[DEBUG] Generated Node Types: {node_types}")
        
        # We expect at least one paragraph and one codeBlock
        self.assertIn("paragraph", node_types)
        self.assertIn("codeBlock", node_types)
        
        # Verify Text Content
        text_node = content_nodes[0]
        self.assertEqual(text_node["type"], "paragraph")
        self.assertEqual(text_node["content"][0]["text"], clean_raw_content)
        
        # Verify Code Block
        # The code block should be the last one usually
        code_block = content_nodes[-1]
        self.assertEqual(code_block["type"], "codeBlock")
        self.assertEqual(code_block["attrs"]["language"], "yaml")
        
        yaml_content = code_block["content"][0]["text"]
        print(f"[DEBUG] YAML Content:\n{yaml_content}")
        
        self.assertIn("version: '1.0'", yaml_content)
        self.assertIn("code_review_params:", yaml_content)
        self.assertIn("gitlab_project_id: 999", yaml_content)

if __name__ == "__main__":
    unittest.main()
