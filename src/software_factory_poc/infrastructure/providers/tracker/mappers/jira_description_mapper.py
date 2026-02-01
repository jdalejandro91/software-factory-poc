import yaml
from typing import Any, Dict, Optional, List

from software_factory_poc.application.core.domain.entities.task import TaskDescription
from software_factory_poc.infrastructure.observability.logger_factory_service import LoggerFactoryService

logger = LoggerFactoryService.build_logger(__name__)

class JiraDescriptionMapper:
    """
    Service responsible for converting between Domain TaskDescription and Jira ADF (Atlassian Document Format).
    Ensures safe handling of automation metadata by encapsulating it in strict code blocks.
    """

    def to_domain(self, adf_json: Optional[Dict[str, Any]]) -> TaskDescription:
        """
        Parses a Jira ADF JSON object into a domain TaskDescription.
        """
        if not adf_json or "content" not in adf_json:
            return TaskDescription(human_text="", automation_metadata=None)

        human_text_parts = []
        automation_metadata = None

        # Iterate through top-level content nodes
        for node in adf_json.get("content", []):
            node_type = node.get("type")
            
            # 1. Extract Human Text from Paragraphs
            if node_type == "paragraph":
                # Paragraphs contain a list of 'text' nodes
                paragraph_text = "".join(
                    [chunk.get("text", "") for chunk in node.get("content", []) if chunk.get("type") == "text"]
                )
                if paragraph_text.strip():
                     human_text_parts.append(paragraph_text)

            # 2. Extract Automation Metadata from YAML Code Blocks
            elif node_type == "codeBlock":
                # Check for YAML language attribute or content inspection
                # Code blocks have a 'content' list usually with one text node
                block_content = "".join(
                    [chunk.get("text", "") for chunk in node.get("content", []) if chunk.get("type") == "text"]
                )
                
                # Heuristic: Check if it looks like our automation block
                if "automation_result:" in block_content:
                    try:
                        # Try to parse the YAML content
                        parsed = yaml.safe_load(block_content)
                        if parsed and isinstance(parsed, dict) and "automation_result" in parsed:
                            automation_metadata = parsed["automation_result"]
                    except yaml.YAMLError:
                        logger.warning("Found potential automation code block but failed to parse YAML.")

        return TaskDescription(
            human_text="\n\n".join(human_text_parts),
            automation_metadata=automation_metadata
        )

    def to_adf(self, description: TaskDescription) -> Dict[str, Any]:
        """
        Converts a domain TaskDescription into a Jira ADF JSON object.
        Injects automation metadata as a strictly formatted YAML code block.
        """
        # Root ADF structure
        adf = {
            "version": 1,
            "type": "doc",
            "content": []
        }

        # 1. Add Human Text (Paragraph)
        if description.human_text:
            paragraph_node = {
                "type": "paragraph",
                "content": [
                    {
                        "type": "text", 
                        "text": description.human_text
                    }
                ]
            }
            adf["content"].append(paragraph_node)

        # 2. Add Automation Context (Code Block)
        if description.has_metadata():
            # Add Separator/Heading
            separator_node = {
                "type": "paragraph",
                "content": [
                    {
                        "type": "text", 
                        "text": "\n🤖 Automation Context (Machine Generated)",
                        "marks": [{"type": "strong"}]
                    }
                ]
            }
            adf["content"].append(separator_node)

            # Serialize Metadata to YAML
            # We wrap it in a root key 'automation_result' for consistency with extraction logic
            wrapper = {"automation_result": description.automation_metadata}
            yaml_str = yaml.dump(wrapper, sort_keys=False, default_flow_style=False)

            # Create Code Block Node
            code_block_node = {
                "type": "codeBlock",
                "attrs": {"language": "yaml"},
                "content": [
                    {
                        "type": "text",
                        "text": yaml_str
                    }
                ]
            }
            adf["content"].append(code_block_node)

        return adf
