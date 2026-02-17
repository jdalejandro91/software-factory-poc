import re
from typing import Any

import yaml

from software_factory_poc.core.domain.mission.entities.mission import TaskDescription
from software_factory_poc.infrastructure.observability.logger_factory_service import (
    LoggerFactoryService,
)

logger = LoggerFactoryService.build_logger(__name__)


class JiraDescriptionMapper:
    """
    Service responsible for converting between Domain TaskDescription and Jira ADF (Atlassian Document Format).
    Ensures safe handling of automation metadata by encapsulating it in strict code blocks.
    Refactored to match strict TaskDescription contract (raw_content + config).
    """

    # Robust Regex for Code Blocks (Markdown ``` or Jira {code})
    CODE_BLOCK_PATTERN = re.compile(
        r"(?:```(?:scaffolder|yaml|yml)?|\{code(?:[:|][^\}]*)?\})\s*([\s\S]*?)\s*(?:```|\{code\})",
        re.IGNORECASE | re.DOTALL,
    )

    def to_domain(self, adf_json: dict[str, Any] | None) -> TaskDescription:
        """
        Parses a Jira ADF JSON object into a domain TaskDescription using a robust Regex strategy.
        1. Flattens ADF to raw text.
        2. Applies Regex to find YAML/Code block.
        3. Returns strictly typed TaskDescription.
        """
        if not adf_json or "content" not in adf_json:
            return TaskDescription(raw_content="", config={})

        # 1. Flatten ADF to Raw Text
        raw_text_parts = []
        for node in adf_json.get("content", []):
            if "content" in node:
                node_text = "".join(
                    [
                        chunk.get("text", "")
                        for chunk in node.get("content", [])
                        if chunk.get("type") == "text"
                    ]
                )
                if node_text:
                    raw_text_parts.append(node_text)

        original_cleaned_text = "\n\n".join(raw_text_parts)

        logger.info(
            f"Scanning Description ({len(original_cleaned_text)} chars) for Config Block..."
        )

        # 2. Extract Config using Robust Regex
        extracted_config: dict[str, Any] = {}
        match = self.CODE_BLOCK_PATTERN.search(original_cleaned_text)
        logger.info(f"Match Found: {bool(match)}")

        if match:
            raw_yaml = match.group(1)
            clean_yaml = raw_yaml.replace("\xa0", " ").strip()

            try:
                parsed = yaml.safe_load(clean_yaml)
                if isinstance(parsed, dict):
                    extracted_config = parsed
                else:
                    logger.warning("Parsed YAML matches pattern but is not a dictionary.")
            except yaml.YAMLError as e:
                logger.warning(f"Failed to parse YAML block in description: {e}")

            original_cleaned_text = original_cleaned_text.replace(match.group(0), "").strip()
            logger.info("Config Block STRIPPED successfully.")

        # 3. Return Domain Entity
        return TaskDescription(raw_content=original_cleaned_text, config=extracted_config or {})
