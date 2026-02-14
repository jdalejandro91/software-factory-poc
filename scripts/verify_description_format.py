import sys
import os
import json

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from software_factory_poc.infrastructure.entrypoints.api.mappers.jira_payload_mapper import JiraPayloadMapper
from software_factory_poc.infrastructure.adapters.drivers.tracker.mappers.jira_description_mapper import JiraDescriptionMapper
from software_factory_poc.domain.entities.task import TaskDescription, Task

def verify_format():
    # 1. Setup Sample Data
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
    parsed_desc: TaskDescription = JiraPayloadMapper._parse_description_config(original_description)
    
    print(f"✅ Parsed Config keys: {list(parsed_desc.config.keys())}")
    print(f"✅ Clean Raw Content:\n{repr(parsed_desc.raw_content)}")

    # Verify that raw_content does NOT contain the code block
    if "{code" in parsed_desc.raw_content:
        print("❌ FAIL: Clean Raw Content still contains '{code}' block!")
    
    # 3. Simulate Entity Update
    task = Task(
        id="1", key="TEST-1", event_type="update", status="Open", 
        summary="Test", project_key="PROJ", issue_type="Task", 
        created_at=0, reporter=None, 
        description=parsed_desc
    )
    
    updated_task = task.update_metadata(new_context)
    print(f"\n✅ Updated Config keys: {list(updated_task.description.config.keys())}")
    
    # Verify nesting in update
    params = updated_task.description.config.get("code_review_params", {})
    if params.get("id") != 12345:
        print(f"❌ FAIL: code_review_params nested merge failed! Got: {params}")
        sys.exit(1)

    # 4. Simulate JiraProvider Assembly (Native ADF)
    print("\n🏗️  Simulating JiraProvider Assembly (Native ADF)...")
    
    mapper = JiraDescriptionMapper()
    adf_payload = mapper.to_adf(updated_task.description)
    
    print("--- FINAL ADF OUTPUT ---")
    print(json.dumps(adf_payload, indent=2))
    print("------------------------")

    # 5. Verification
    # Check structure
    if adf_payload.get("type") != "doc":
        print(f"❌ FAIL: Expected type 'doc', found {adf_payload.get('type')}")
        sys.exit(1)
        
    content_nodes = adf_payload.get("content", [])
    
    # Identify nodes
    has_text = any(n["type"] == "paragraph" for n in content_nodes if any("Start of Description" in t.get("text", "") for t in n.get("content", [])))
    
    code_blocks = [n for n in content_nodes if n["type"] == "codeBlock"]
    
    if not has_text:
        print("❌ FAIL: Original text paragraph not found in ADF!")
        sys.exit(1)

    if len(code_blocks) != 1:
        print(f"❌ FAIL: Expected exactly 1 codeBlock, found {len(code_blocks)}")
        sys.exit(1)
        
    yaml_node = code_blocks[0]
    if yaml_node.get("attrs", {}).get("language") != "yaml":
        print(f"❌ FAIL: CodeBlock language is not YAML!")
        sys.exit(1)
        
    yaml_text = yaml_node["content"][0]["text"]
    
    print("\n✅ SUCCESS: Description format verified (Native ADF).")
    print(f"   - Original text preserved in Paragraph: {has_text}")
    print(f"   - Native CodeBlock verified: True")
    print(f"   - Nested Config verified: {'code_review_params' in yaml_text}")
    print(f"   - Old config preserved: {'framework: fastAPI' in yaml_text}")

if __name__ == "__main__":
    verify_format()
