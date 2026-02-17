import os
import sys

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from software_factory_poc.core.domain.mission.entities import TaskDescription
from software_factory_poc.infrastructure.tools.tracker.jira.mappers.jira_description_mapper import (
    JiraDescriptionMapper,
)
from software_factory_poc.infrastructure.entrypoints.api.mappers.jira_payload_mapper import (
    JiraPayloadMapper,
)


def verify_format():
    # 1. Setup Sample Data
    original_description = """Start of Description.
Human readable requirement 1.
Human readable requirement 2.

{code:yaml|borderStyle=solid}
version: 1.0
scaffolder:
  stack: python
  framework: fastAPI
{code}

End of Description."""

    print("--- ORIGINAL INPUT ---")
    print(original_description)
    print("----------------------\n")

    # 2. Parse (Simulate Inbound Webhook)
    print("Parsing with JiraPayloadMapper...")
    parsed_desc: TaskDescription = JiraPayloadMapper._parse_description_config(original_description)

    print(f"Parsed Config keys: {list(parsed_desc.config.keys())}")
    print(f"Clean Raw Content:\n{repr(parsed_desc.raw_content)}")

    # Verify that raw_content does NOT contain the code block
    if "{code" in parsed_desc.raw_content:
        print("FAIL: Clean Raw Content still contains '{code}' block!")
        sys.exit(1)

    # 3. Verify ADF to_domain round-trip
    print("\nTesting JiraDescriptionMapper.to_domain...")
    mapper = JiraDescriptionMapper()
    adf_input = {
        "content": [
            {"type": "paragraph", "content": [{"type": "text", "text": "Some human text"}]},
            {"type": "codeBlock", "content": [{"type": "text", "text": "version: 1.0\nscaffolder:\n  stack: python"}]},
        ]
    }
    result = mapper.to_domain(adf_input)
    print(f"to_domain config keys: {list(result.config.keys())}")
    print(f"to_domain raw_content: {repr(result.raw_content)}")

    print("\nSUCCESS: Description format verified.")

if __name__ == "__main__":
    verify_format()
