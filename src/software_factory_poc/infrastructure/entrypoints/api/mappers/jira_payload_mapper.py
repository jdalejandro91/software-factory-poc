from typing import Any

from software_factory_poc.application.core.domain.agents.scaffolding.scaffolding_order import (
    ScaffoldingOrder,
)
from software_factory_poc.application.core.domain.agents.scaffolding.scaffolding_contract import (
    ScaffoldingContractModel,
)
from software_factory_poc.infrastructure.entrypoints.api.dtos.jira_webhook_dto import JiraWebhookDTO
from software_factory_poc.infrastructure.observability.logger_factory_service import LoggerFactoryService

logger = LoggerFactoryService.build_logger(__name__)

class JiraPayloadMapper:
    """
    Maps incoming Jira Webhook payloads to internal Domain Commands (ScaffoldingOrder).
    Extracts Scaffolding Contract (YAML) from issue description.
    """

    @classmethod
    def map_to_request(cls, payload: dict | JiraWebhookDTO) -> ScaffoldingOrder:
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

        # Extract and Validate Contract using Smart Contract Factory
        # This handles block extraction (Markdown/Jira) and YAML/JSON parsing internally
        try:
            contract = ScaffoldingContractModel.from_raw_text(description)
        except Exception as e:
            logger.error(f"Failed to parse scaffolding contract for {issue_key}: {e}")
            raise ValueError(f"Invalid Scaffolding Contract in Jira Description: {e}")

        # Map to Domain Request
        return ScaffoldingOrder(
            issue_key=issue_key,
            summary=summary,
            raw_instruction=description, # We keep raw description as context
            reporter=reporter,
            # Derived from Contract:
            technology_stack=contract.technology_stack,
            repository_url=f"https://gitlab.com/{contract.gitlab.project_path}" if contract.gitlab.project_path else None,
            project_id=str(contract.gitlab.project_id) if contract.gitlab.project_id else None
            # parameters can be added to ScaffoldingOrder if we modify the entity
        )
