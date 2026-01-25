from typing import Any, Union 

from software_factory_poc.application.core.agents.scaffolding.value_objects.scaffolding_order import (
    ScaffoldingOrder,
)

from software_factory_poc.infrastructure.entrypoints.api.dtos.jira_webhook_dto import JiraWebhookDTO
from software_factory_poc.infrastructure.observability.logger_factory_service import LoggerFactoryService

logger = LoggerFactoryService.build_logger(__name__)

class JiraPayloadMapper:
    """
    Maps incoming Jira Webhook payloads to internal Domain Commands (ScaffoldingOrder).
    """

    @classmethod
    def map_to_request(cls, payload: Union[dict, JiraWebhookDTO]) -> ScaffoldingOrder:
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

        # Map to Domain Request
        return ScaffoldingOrder(
            issue_key=issue_key,
            raw_instruction=description, # We keep raw description as context
            summary=summary,
            reporter=reporter,
            # The domain will parse the contract from raw_instruction
        )
