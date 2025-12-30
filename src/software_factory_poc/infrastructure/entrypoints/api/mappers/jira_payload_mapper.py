import re
import yaml
from typing import Any

from software_factory_poc.application.core.domain.entities.scaffolding.scaffolding_request import (
    ScaffoldingRequest,
)
from software_factory_poc.application.core.domain.entities.scaffolding.scaffolding_contract import (
    ScaffoldingContractModel,
)
from software_factory_poc.infrastructure.entrypoints.api.dtos.jira_webhook_dto import JiraWebhookDTO
from software_factory_poc.infrastructure.observability.logger_factory_service import LoggerFactoryService

logger = LoggerFactoryService.build_logger(__name__)

class JiraPayloadMapper:
    """
    Maps incoming Jira Webhook payloads to internal Domain Commands (ScaffoldingRequest).
    Extracts Scaffolding Contract (YAML) from issue description.
    """

    # Regex to find content between ```scaffolding and ```
    CONTRACT_REGEX = r"```scaffolding\n(.*?)\n```"

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

        # Extract YAML Contract
        yaml_content = cls._extract_yaml(description)
        
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
    def _extract_yaml(cls, description: str) -> dict[str, Any]:
        match = re.search(cls.CONTRACT_REGEX, description, re.DOTALL)
        if not match:
             raise ValueError("No scaffolding contract found (block ```scaffolding ... ``` missing).")
        
        yaml_str = match.group(1)
        try:
            return yaml.safe_load(yaml_str)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML found in contract block: {e}")
