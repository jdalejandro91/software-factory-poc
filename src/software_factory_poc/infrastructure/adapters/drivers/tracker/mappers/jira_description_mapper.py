import re
import yaml
from typing import Any, Dict, Optional

from software_factory_poc.domain.entities.task import TaskDescription
from software_factory_poc.infrastructure.observability.logger_factory_service import LoggerFactoryService
from software_factory_poc.infrastructure.adapters.drivers.tracker.mappers.jira_adf_primitives import JiraAdfPrimitives

logger = LoggerFactoryService.build_logger(__name__)


class JiraDescriptionMapper:
    """
    Service responsible for converting between Domain TaskDescription and Jira ADF (Atlassian Document Format).
    Ensures safe handling of automation metadata by encapsulating it in strict code blocks.
    Refactored to match strict TaskDescription contract (raw_content + config).
    """

    # Robust Regex for Code Blocks (Markdown ``` or Jira {code})
    # Captures content inside the block.
    # Robust Pattern: Handles attributes by matching any char until closing brace logic
    CODE_BLOCK_PATTERN = re.compile(
        r"(?:```(?:scaffolding|yaml|yml)?|\{code(?:[:|][^\}]*)?\})\s*([\s\S]*?)\s*(?:```|\{code\})",
        re.IGNORECASE | re.DOTALL
    )

    def to_domain(self, adf_json: Optional[Dict[str, Any]]) -> TaskDescription:
        """
        Parses a Jira ADF JSON object into a domain TaskDescription using a robust Regex strategy.
        1. Flattens ADF to raw text.
        2. Applies Regex to find YAML/Code block.
        3. Returns strictly typed TaskDescription.
        """
        if not adf_json or "content" not in adf_json:
            return TaskDescription(raw_content="", config={})

        # 1. Flatten ADF to Raw Text
        # Iterate over all content nodes to reconstruct the full textual representation
        raw_text_parts = []
        for node in adf_json.get("content", []):
            # Extract text from any node that has content (paragraphs, codeBlocks, headings, etc.)
            if "content" in node:
                node_text = "".join(
                    [chunk.get("text", "") for chunk in node.get("content", []) if chunk.get("type") == "text"]
                )
                if node_text:
                    raw_text_parts.append(node_text)
        
        
        # Join with double newlines to separate blocks clearly
        original_cleaned_text = "\n\n".join(raw_text_parts)
        
        logger.info(f"🔎 Scanning Description ({len(original_cleaned_text)} chars) for Config Block...")

        # 2. Extract Config using Robust Regex
        extracted_config = {}
        match = self.CODE_BLOCK_PATTERN.search(original_cleaned_text)
        logger.info(f"🧩 Match Found: {bool(match)}")

        if match:
            raw_yaml = match.group(1)
            # Sanitize invisible chars (common in Jira copy-paste)
            clean_yaml = raw_yaml.replace(u'\xa0', ' ').strip()
            
            try:
                parsed = yaml.safe_load(clean_yaml)
                if isinstance(parsed, dict):
                    extracted_config = parsed
                else:
                    logger.warning("Parsed YAML matches pattern but is not a dictionary.")
            except yaml.YAMLError as e:
                logger.warning(f"Failed to parse YAML block in description: {e}")
            
            # Remove the configuration block from the raw text
            original_cleaned_text = original_cleaned_text.replace(match.group(0), "").strip()
            logger.info("✂️  Config Block STRIPPED successfully.")

        # 3. Return Domain Entity
        # Critical: Must match TaskDescription(raw_content=..., config=...)
        return TaskDescription(
            raw_content=original_cleaned_text,
            config=extracted_config or {}
        )

    def to_adf(self, description: TaskDescription) -> Dict[str, Any]:
        """
        Converts a domain TaskDescription into a native Jira ADF JSON object.
        - Maps 'raw_content' to a standard Paragraph node.
        - Maps 'config' dictionary to a specific 'codeBlock' node (language=yaml).
        """
        content_nodes = []

        # 1. Human Text (Paragraph Node)
        if description.raw_content:
            clean_text = description.raw_content.strip()
            if clean_text:
                # Add text paragraph
                paragraph_node = JiraAdfPrimitives.create_paragraph([
                    JiraAdfPrimitives.create_text(clean_text)
                ])
                content_nodes.append(paragraph_node)

        # 2. YAML Configuration (Native Code Block Node)
        if description.config:
            try:
                # Dump YAML preserving order
                yaml_str = yaml.dump(
                    description.config, 
                    sort_keys=False, 
                    default_flow_style=False, 
                    allow_unicode=True
                ).strip()

                # Add spacing paragraph if text exists
                if content_nodes:
                    content_nodes.append(JiraAdfPrimitives.create_paragraph([]))

                # Create the dedicated Code Block node using primitives
                # This ensures Jira renders it as a highlighted box, not plain text.
                code_block_node = JiraAdfPrimitives.create_code_block(yaml_str, language="yaml")
                content_nodes.append(code_block_node)
                
            except Exception as e:
                logger.error(f"Failed to dump config to YAML in to_adf: {e}")
                # Fallback error text
                content_nodes.append(JiraAdfPrimitives.create_paragraph([
                     JiraAdfPrimitives.create_text("Error rendering configuration block.")
                ]))

        # Return the full ADF Document
        return JiraAdfPrimitives.create_doc(content_nodes)