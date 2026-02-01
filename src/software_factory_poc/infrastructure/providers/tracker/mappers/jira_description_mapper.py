from typing import Any, Dict, Optional

import yaml

from software_factory_poc.application.core.domain.entities.task import TaskDescription
from software_factory_poc.infrastructure.observability.logger_factory_service import LoggerFactoryService

logger = LoggerFactoryService.build_logger(__name__)

class JiraDescriptionMapper:
    """
    Service responsible for converting between Domain TaskDescription and Jira ADF (Atlassian Document Format).
    Ensures safe handling of automation metadata by encapsulating it in a unified YAML code block.
    """

    def to_domain(self, adf_json: Optional[Dict[str, Any]]) -> TaskDescription:
        """
        Parses a Jira ADF JSON object into a domain TaskDescription.
        Supports Unified YAML Block (Extraction of both Scaffolding & Automation data from a single block).
        """
        if not adf_json or "content" not in adf_json:
            return TaskDescription(human_text="", automation_metadata=None)

        human_text_parts = []
        automation_metadata = None
        description_scaffolding_params = None

        # Iterate through top-level content nodes
        for node in adf_json.get("content", []):
            node_type = node.get("type")
            
            # 1. Extract Human Text from Paragraphs
            if node_type == "paragraph":
                paragraph_text = "".join(
                    [chunk.get("text", "") for chunk in node.get("content", []) if chunk.get("type") == "text"]
                )
                if paragraph_text.strip():
                     human_text_parts.append(paragraph_text)

            # 2. Extract Data from YAML Code Blocks
            elif node_type == "codeBlock":
                block_content = "".join(
                    [chunk.get("text", "") for chunk in node.get("content", []) if chunk.get("type") == "text"]
                )
                
                try:
                    parsed = yaml.safe_load(block_content)
                    if isinstance(parsed, dict):
                        # A. Extract Automation metadata if present
                        if "automation_result" in parsed:
                            automation_metadata = parsed["automation_result"]
                        
                        # B. Extract Scaffolding Params
                        # Heuristic: Check for characteristic keys of scaffolding
                        scaffolding_keys = ["technology_stack", "target", "version", "parameters"]
                        has_scaffolding_keys = any(k in parsed for k in scaffolding_keys)
                        
                        if has_scaffolding_keys:
                            # Create a clean copy for scaffolding params (excluding the result to avoid duplication)
                            clean_params = parsed.copy()
                            if "automation_result" in clean_params:
                                del clean_params["automation_result"]
                            
                            # Assign if not already found (First Valid Block wins strategy)
                            if not description_scaffolding_params and clean_params:
                                description_scaffolding_params = clean_params
                                
                except (yaml.YAMLError, AttributeError):
                    logger.warning("Found code block but failed to parse as valid YAML dict.")

        return TaskDescription(
            human_text="\n\n".join(human_text_parts),
            automation_metadata=automation_metadata,
            scaffolding_params=description_scaffolding_params
        )

    def to_adf(self, description: TaskDescription) -> Dict[str, Any]:
        """
        Converts a domain TaskDescription into a Jira ADF JSON object.
        Merges Scaffolding Params and Automation Metadata into a single Unified YAML Block.
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

        # 2. Unified YAML Block Construction
        combined_data = {}
        
        # Merge Scaffolding Params first (so they appear at top of the YAML)
        if description.has_scaffolding_params():
            combined_data.update(description.scaffolding_params)
        
        # Merge Automation Result (nested under its own key)
        if description.has_metadata():
            combined_data["automation_result"] = description.automation_metadata

        if combined_data:
            # Header
            header_node = {
                "type": "paragraph",
                "content": [
                    {
                        "type": "text", 
                        "text": "\n📋 Scaffolding Context & Automation Result",
                        "marks": [{"type": "strong"}]
                    }
                ]
            }
            adf["content"].append(header_node)

            # Serialize to YAML
            # sort_keys=False ensures scaffolding params stay at top if inserted first
            yaml_str = yaml.dump(combined_data, sort_keys=False, default_flow_style=False, allow_unicode=True)
            
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
