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

    def test_update_metadata_merges_config_only(self):
        new_ctx = {"param2": "value2"}
        updated_task = self.task.update_metadata(new_ctx)

        # 1. Check Config Merged
        self.assertEqual(updated_task.description.config["param1"], "value1")
        self.assertEqual(updated_task.description.config["param2"], "value2")

        # 2. Check Raw Content UNCHANGED
        self.assertEqual(updated_task.description.raw_content, self.base_raw)

    def test_smart_merge_logic(self):
        base_cfg = {
            "root_val": 1,
            "code_review_params": {
                "existing_param": "keep_me"
            }
        }
        task_merge = Task(
             id="4", key="T-4", summary="Merge", status="Todo", project_key="PROJ", issue_type="Task",
             description=TaskDescription(raw_content="Text", config=base_cfg)
        )
        
        # Update with new sub-key in code_review_params
        update_ctx = {
            "code_review_params": {
                "new_param": "add_me"
            },
            "root_val": 2
        }
        
        updated_task = task_merge.update_metadata(update_ctx)
        
        new_cfg = updated_task.description.config
        # Check merge
        self.assertEqual(new_cfg["code_review_params"]["existing_param"], "keep_me")
        self.assertEqual(new_cfg["code_review_params"]["new_param"], "add_me")
        # Check overwrite
        self.assertEqual(new_cfg["root_val"], 2)

    def test_immutability(self):
        new_ctx = {"changed": True}
        updated_task = self.task.update_metadata(new_ctx)
        
        self.assertNotEqual(id(self.task), id(updated_task))
        self.assertNotEqual(self.task.description.config, updated_task.description.config)
        # Original should remain untouched
        self.assertEqual(self.task.description.config, self.base_config)

if __name__ == "__main__":
    unittest.main()
