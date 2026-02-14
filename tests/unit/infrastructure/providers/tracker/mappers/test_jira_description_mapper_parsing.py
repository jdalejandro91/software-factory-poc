import unittest
from software_factory_poc.infrastructure.providers.tracker.mappers.jira_description_mapper import JiraDescriptionMapper

class TestJiraDescriptionMapperParsing(unittest.TestCase):
    
    def setUp(self):
        self.mapper = JiraDescriptionMapper()
        
    def test_to_domain_strips_config(self):
        # 1. Setup Input: Text + Jira YAML Block
        # We manually construction the expected structure from ADF flattening logic
        # But to test to_domain, we need to pass a dict that simulates the ADF structure
        # or we can test the regex/parsing logic if we could access it directly?
        # The instruction says "Mock a Jira Issue object", but to_domain takes adf_json dict.
        
        input_text = "Text\n{code:yaml}foo: bar{code}"
        
        # Simulating ADF structure for "Text\n{code:yaml}foo: bar{code}"
        # A simple paragraph containing this text
        adf_json = {
            "version": 1,
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": input_text
                        }
                    ]
                }
            ]
        }
        
        # 2. Execution
        task_desc = self.mapper.to_domain(adf_json)
        
        # 3. Assertions
        print(f"DEBUG: Parsed Raw Content: '{task_desc.raw_content}'")
        print(f"DEBUG: Parsed Config: {task_desc.config}")

        # Assert raw content is clean
        self.assertEqual(task_desc.raw_content.strip(), "Text")
        
        # Assert config is parsed
        self.assertEqual(task_desc.config, {"foo": "bar"})

if __name__ == "__main__":
    unittest.main()
