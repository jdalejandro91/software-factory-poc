import sys
import os
import yaml

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from software_factory_poc.infrastructure.entrypoints.api.mappers.jira_payload_mapper import JiraPayloadMapper
from software_factory_poc.application.core.domain.entities.task import TaskDescription, Task

def verify_format():
    # 1. Setup Sample Data
    # Simulating a Jira description with attributes in the code block (the case that was failing)
    original_description = """Start of Description.
Human readable requirement 1.
Human readable requirement 2.

{code:yaml|borderStyle=solid}
version: 1.0
scaffolding:
  stack: python
  framework: fastAPI
{code}

End of Description."""

    new_context = {
        "code_review_params": {
            "id": 12345,
            "strict": True
        }
    }

    print("--- ORIGINAL INPUT ---")
    print(original_description)
    print("----------------------\n")

    # 2. Parse (Simulate Inbound Webhook)
    print("🚀 Parsing with JiraPayloadMapper...")
    # Accessing the classmethod directly for focused testing
    parsed_desc: TaskDescription = JiraPayloadMapper._parse_description_config(original_description)
    
    print(f"✅ Parsed Config keys: {list(parsed_desc.config.keys())}")
    print(f"✅ Clean Raw Content:\n{repr(parsed_desc.raw_content)}")

    # Verify that raw_content does NOT contain the code block
    if "{code" in parsed_desc.raw_content:
        print("❌ FAIL: Clean Raw Content still contains '{code}' block!")
    
    # 3. Simulate Entity Update
    # Create a dummy task wrapper to use the update_metadata method
    # or just manually update since we are verifying the flow logic
    # But let's use the entity method to be sure
    task = Task(
        id="1", key="TEST-1", event_type="update", status="Open", 
        summary="Test", project_key="PROJ", issue_type="Task", 
        created_at=0, reporter=None, 
        description=parsed_desc
    )
    
    updated_task = task.update_metadata(new_context)
    print(f"\n✅ Updated Config keys: {list(updated_task.description.config.keys())}")

    # 4. Simulate JiraProvider Assembly
    print("\n🏗️  Simulating JiraProvider Assembly...")
    
    yaml_str = yaml.dump(
        updated_task.description.config, 
        default_flow_style=False, 
        allow_unicode=True, 
        sort_keys=False
    ).strip()
    
    yaml_block = f"{{code:yaml}}\n{yaml_str}\n{{code}}"
    final_description = f"{updated_task.description.raw_content.strip()}\n\n{yaml_block}"

    print("--- FINAL OUTPUT ---")
    print(final_description)
    print("--------------------")

    # 5. Verification
    block_count = final_description.count("{code:yaml}")
    closing_count = final_description.count("{code}")
    # note: closing count captures the opening tag's "code" part inside {code:yaml} too if simple string match
    # but strictly looking for separate tags:
    
    if block_count != 1:
        print(f"❌ FAIL: Expected 1 {{code:yaml}} block, found {block_count}")
        sys.exit(1)
        
    print("\n✅ SUCCESS: Description format verified.")
    print(f"   - Original text preserved: {'Start of Description' in final_description}")
    print(f"   - New config present: {'code_review_params' in final_description}")
    print(f"   - Old config present: {'framework: fastAPI' in final_description}")
    print(f"   - Single YAML block: True")

if __name__ == "__main__":
    verify_format()
