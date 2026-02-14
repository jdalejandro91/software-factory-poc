import unittest
import yaml
from software_factory_poc.infrastructure.entrypoints.api.mappers.jira_payload_mapper import JiraPayloadMapper
from software_factory_poc.application.core.agents.scaffolding.scaffolding_agent import Task

class TestJiraDescriptionAssembly(unittest.TestCase):
    
    def test_full_description_assembly(self):
        # 1. SETUP: Simulating incoming Jira Payload
        # Text "Reqs." followed by a YAML block
        input_text = """Reqs.
{code:yaml}
version: 1.0
params:
  a: 1
{code}"""
        
        # We assume the mapper extracts description from a specific structure
        # mocking the payload dict structure expected by proper Mapper usage or direct method call if possible.
        # to_domain takes a dict.
        payload = {
            "issue": {
                "key": "TEST-1",
                "id": "100",
                "fields": {
                    "summary": "Test Summary",
                    "description": input_text,
                    "project": {"key": "PROJ"},
                    "status": {"name": "Open"},
                    "issuetype": {"name": "Task"}
                }
            },
            "user": {
                "name": "tester",
                "displayName": "Tester",
                "active": True
            },
            "webhookEvent": "jira:issue_updated",
            "timestamp": 1234567890
        }

        # 2. EXECUTION STEP A: Parsing (Mapper)
        task = JiraPayloadMapper.to_domain(payload)
        
        # ASSERT A: Separation of concerns
        # raw_content should be STRIPPED of the yaml block
        print(f"\n[DEBUG] Raw Content after parsing: {repr(task.description.raw_content)}")
        self.assertEqual(task.description.raw_content.strip(), "Reqs.")
        
        # config should be populated
        expected_config = {"version": 1.0, "params": {"a": 1}}
        self.assertEqual(task.description.config, expected_config)
        
        # 3. EXECUTION STEP B: Merging (Entity)
        update_data = {
            "code_review_params": {
                "id": 99
            }
        }
        updated_task = task.update_metadata(update_data)
        
        # ASSERT B: Merging successful
        print(f"[DEBUG] config after update: {updated_task.description.config}")
        self.assertEqual(updated_task.description.config["version"], 1.0)
        self.assertEqual(updated_task.description.config["code_review_params"]["id"], 99)
        self.assertEqual(updated_task.description.config["params"]["a"], 1)
        
        # 4. EXECUTION STEP C: Assembly (Provider Simulation)
        # Verify the logic implemented in JiraProviderImpl.update_task_description
        
        # Generate YAML
        yaml_str = yaml.dump(
            updated_task.description.config, 
            default_flow_style=False, 
            allow_unicode=True, 
            sort_keys=False
        ).strip()
        
        # Format Block
        yaml_block = f"{{code:yaml}}\n{yaml_str}\n{{code}}"
        
        # Assemble
        final_description = f"{updated_task.description.raw_content.strip()}\n\n{yaml_block}"
        
        print(f"\n[DEBUG] Final Assembled Description:\n{final_description}")
        
        # ASSERT C: Final Output Quality
        # 1. Contains original text
        self.assertTrue(final_description.startswith("Reqs."))
        
        # 2. Contains ONLY ONE code block
        self.assertEqual(final_description.count("{code:yaml}"), 1, "Should have exactly one opening tag {code:yaml}")
        self.assertEqual(final_description.count("{code}"), 1, "Should have exactly one closing tag {code}")
        
        # 3. Contains merged data
        self.assertIn("version: 1.0", final_description)
        self.assertIn("id: 99", final_description)
        self.assertIn("a: 1", final_description)
        
        # 4. Correct indentation (YAML structure)
        # Params `a` should be indented
        self.assertIn("\n  a: 1", final_description)
        self.assertIn("\n  id: 99", final_description) # code_review_params is a dict too

if __name__ == "__main__":
    unittest.main()
