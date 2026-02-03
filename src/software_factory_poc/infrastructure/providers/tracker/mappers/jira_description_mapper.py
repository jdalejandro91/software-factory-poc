import re
import yaml
from typing import Any, Dict, Optional

from software_factory_poc.application.core.domain.entities.task import TaskDescription
from software_factory_poc.infrastructure.observability.logger_factory_service import LoggerFactoryService

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
        Converts a domain TaskDescription into a Jira ADF JSON object.
        Simple implementation: Puts raw content into a paragraph. 
        Detailed reconstruction from 'config' is skipped as we assume raw_content holds the source of truth.
        """
        adf = {
            "version": 1,
            "type": "doc",
            "content": []
        }

        if description.raw_content:
            # Split by newlines to avoid massive single line
            lines = description.raw_content.split('\n')
            # For better formatting, we could try to detect code blocks, but for now, 
            # safety first: simplistic text rendering.
             
            paragraph_node = {
                "type": "paragraph",
                "content": [
                    {
                        "type": "text",
                        "text": description.raw_content
                    }
                ]
            }
            adf["content"].append(paragraph_node)

        return adf