import unittest
from software_factory_poc.application.core.domain.entities.task import Task, TaskDescription
import yaml

class TestTaskMetadata(unittest.TestCase):

    def setUp(self):
        self.base_config = {"param1": "value1"}
        self.base_raw = "Start description\n```yaml\nparam1: value1\n```\nEnd description"
        self.task = Task(
            id="1", key="T-1", summary="Test", status="Todo", project_key="PROJ", issue_type="Task",
            description=TaskDescription(
                raw_content=self.base_raw, 
                config=self.base_config
            )
        )

    def test_update_metadata_replaces_block(self):
        new_ctx = {"param2": "value2"}
        updated_task = self.task.update_metadata(new_ctx)

        # 1. Check Config Merged
        self.assertEqual(updated_task.description.config["param1"], "value1")
        self.assertEqual(updated_task.description.config["param2"], "value2")

        # 2. Check Raw Content Updated
        self.assertIn("param2: value2", updated_task.description.raw_content)
        # Should preserve surrounding text
        self.assertIn("Start description", updated_task.description.raw_content)
        self.assertIn("End description", updated_task.description.raw_content)
        # Should NOT have duplicate blocks (rough check)
        self.assertEqual(updated_task.description.raw_content.count("```yaml"), 1)

    def test_update_metadata_appends_block_if_missing(self):
        task_no_yaml = Task(
            id="2", key="T-2", summary="NoYaml", status="Todo", project_key="PROJ", issue_type="Task",
            description=TaskDescription(raw_content="Just text", config={})
        )
        
        updated_task = task_no_yaml.update_metadata({"new": "data"})
        
        self.assertIn("Just text", updated_task.description.raw_content)
        self.assertIn("new: data", updated_task.description.raw_content)
        self.assertIn("```yaml", updated_task.description.raw_content)

    def test_immutability(self):
        new_ctx = {"changed": True}
        updated_task = self.task.update_metadata(new_ctx)
        
        self.assertNotEqual(id(self.task), id(updated_task))
        self.assertNotEqual(self.task.description.config, updated_task.description.config)
        # Original should remain untouched
        self.assertEqual(self.task.description.config, self.base_config)

if __name__ == "__main__":
    unittest.main()
