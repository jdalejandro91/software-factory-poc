import unittest
from software_factory_poc.infrastructure.entrypoints.api.mappers.jira_payload_mapper import JiraPayloadMapper
from software_factory_poc.application.core.domain.entities.task import TaskDescription

class TestJiraPayloadMapperSeparation(unittest.TestCase):
    
    def test_separates_yaml_block_from_text(self):
        # Input: Text + YAML Block in Jira format
        input_text = """
Requerimiento de arquitectura:
Necesitamos un microservicio en Python.

{code:yaml}
scaffolding:
  technology_stack:
    language: python
{code}

Footer text.
"""
        # Execute private parsing method validation
        # Since logic is in _parse_description_config, we test that directly if possible or via mocked payload
        # But _parse_description_config returns TaskDescription directly.
        
        result = JiraPayloadMapper._parse_description_config(input_text)
        
        # Assertions
        
        # 1. Config should contain the parsed dict
        self.assertEqual(result.config["scaffolding"]["technology_stack"]["language"], "python")
        
        # 2. Raw Content should NOT contain the YAML block
        self.assertNotIn("{code:yaml}", result.raw_content)
        self.assertNotIn("scaffolding:", result.raw_content)
        
        # 3. Raw Content SHOULD contain the human text
        self.assertIn("Requerimiento de arquitectura", result.raw_content)
        self.assertIn("Footer text", result.raw_content)
        
        # 4. Check clean whitespace (optional, but good for cleanliness)
        clean_text = result.raw_content.strip()
        self.assertTrue(clean_text.startswith("Requerimiento de arquitectura"))

    def test_handles_no_config_block(self):
        input_text = "Just plain text description."
        
        result = JiraPayloadMapper._parse_description_config(input_text)
        
        self.assertEqual(result.config, {})
        self.assertEqual(result.raw_content, input_text)

if __name__ == "__main__":
    unittest.main()
