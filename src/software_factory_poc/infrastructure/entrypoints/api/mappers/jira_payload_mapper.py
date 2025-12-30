import re
import yaml
from typing import Any

from software_factory_poc.application.core.domain.entities.scaffolding.scaffolding_request import (
    ScaffoldingRequest,
)
from software_factory_poc.application.core.domain.entities.scaffolding.scaffolding_contract import (
    ScaffoldingContractModel,
)
from software_factory_poc.application.core.domain.services.helpers.text_block_extractor import TextBlockExtractor
from software_factory_poc.infrastructure.entrypoints.api.dtos.jira_webhook_dto import JiraWebhookDTO
from software_factory_poc.infrastructure.observability.logger_factory_service import LoggerFactoryService

logger = LoggerFactoryService.build_logger(__name__)

class JiraPayloadMapper:
    """
    Maps incoming Jira Webhook payloads to internal Domain Commands (ScaffoldingRequest).
    Extracts Scaffolding Contract (YAML) from issue description.
    """

    @classmethod
    def map_to_request(cls, payload: dict | JiraWebhookDTO) -> ScaffoldingRequest:
        # Normalize input
        if isinstance(payload, JiraWebhookDTO):
            issue_key = payload.issue.key
            summary = payload.issue.fields.summary
            description = payload.issue.fields.description or ""
            reporter = payload.user.display_name
        else:
            # Fallback for dict
            issue = payload.get("issue", {})
            fields = issue.get("fields", {})
            issue_key = issue.get("key", "UNKNOWN")
            summary = fields.get("summary", "No Summary")
            description = fields.get("description", "")
            reporter = payload.get("user", {}).get("displayName", "Unknown")

        # Observability: Log description details
        logger.info(f"Processing Task {issue_key}. Raw Description: {repr(description)}")

        # Extract YAML Contract
        yaml_content = cls._extract_yaml(description, issue_key)
        
        # Validate Contract using Domain Pydantic Model
        # This ensures the contract is syntactically valid before creating the Domain Request
        try:
            contract = ScaffoldingContractModel(**yaml_content)
        except Exception as e:
            logger.error(f"Failed to parse scaffolding contract for {issue_key}: {e}")
            raise ValueError(f"Invalid Scaffolding Contract in Jira Description: {e}")

        # Map to Domain Request
        return ScaffoldingRequest(
            issue_key=issue_key,
            summary=summary,
            raw_instruction=description, # We keep raw description as context
            reporter=reporter,
            # Derived from Contract:
            technology_stack=contract.technology_stack,
            repository_url=f"https://gitlab.com/{contract.gitlab.project_path}" if contract.gitlab.project_path else None,
            project_id=str(contract.gitlab.project_id) if contract.gitlab.project_id else None
            # parameters can be added to ScaffoldingRequest if we modify the entity
        )

    @classmethod
    def _extract_yaml(cls, description: str, issue_key: str) -> dict[str, Any]:
        extracted_text = TextBlockExtractor.extract_block(description)
        
        if not extracted_text:
             logger.warning(f"No scaffolding block matched for {issue_key}. Check regex or input format.")
             raise ValueError("No scaffolding contract found (block ```scaffolding ... ``` or similar missing).")
        
        try:
            return yaml.safe_load(extracted_text)
        except yaml.YAMLError as e:
            logger.error(f"YAML Parse Error for {issue_key}: {e}")
            raise ValueError(f"Invalid YAML found in contract block: {e}")
