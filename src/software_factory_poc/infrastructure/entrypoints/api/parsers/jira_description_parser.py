import re
from typing import Optional

import yaml

from software_factory_poc.application.core.domain.entities.task import TaskDescription
from software_factory_poc.infrastructure.observability.logger_factory_service import LoggerFactoryService

logger = LoggerFactoryService.build_logger(__name__)

class JiraDescriptionParser:
    """
    Utility parser to extract scaffolding configuration from raw Jira descriptions.
    Identifies and removes '```scaffolding' blocks to separate system input from user text.
    """

    @staticmethod
    def parse(raw_text: Optional[str]) -> TaskDescription:
        """
        Parses raw text to extract scaffolding parameters and clean human text.
        """
        if not raw_text:
            return TaskDescription(human_text="", raw_content="")

        scaffolding_params = None
        human_text = raw_text

        # Regex to find the scaffolding block (dotall to match newlines)
        # Matches: ```scaffolding ... ``` OR {code:yaml} ... {code}
        pattern = re.compile(r"(?:```(?:yaml|scaffolding)?|\{code:(?:yaml|scaffolding)?\})\s*(.*?)\s*(?:```|\{code\})", re.DOTALL | re.IGNORECASE)
        match = pattern.search(raw_text)

        if match:
            yaml_content = match.group(1)
            try:
                # Parse YAML content
                parsed_yaml = yaml.safe_load(yaml_content)
                if isinstance(parsed_yaml, dict):
                    scaffolding_params = parsed_yaml
                else:
                    logger.warning("Scaffolding block found but did not parse into a dictionary.")
            except yaml.YAMLError as e:
                logger.warning(f"Failed to parse scaffolding YAML block: {e}")

            # Remove the detected block from the human descriptions
            # Using simple replacement of the matched string
            human_text = raw_text.replace(match.group(0), "").strip()

        return TaskDescription(
            human_text=human_text.strip(),
            raw_content=raw_text,
            scaffolding_params=scaffolding_params
        )
