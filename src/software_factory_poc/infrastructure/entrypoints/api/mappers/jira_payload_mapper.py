from typing import Union

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
        if isinstance(payload, JiraWebhookDTO):
            return cls._extract_from_dto(payload)
        return cls._extract_from_dict(payload)

    @classmethod
    def _extract_from_dto(cls, payload: JiraWebhookDTO) -> ScaffoldingOrder:
        issue_key = payload.issue.key
        description = payload.issue.fields.description or ""
        
        logger.info(f"Processing Task {issue_key}. Raw Description: {repr(description)}")
        
        return ScaffoldingOrder(
            issue_key=issue_key,
            raw_instruction=description,
            summary=payload.issue.fields.summary,
            reporter=payload.user.display_name
        )

    @classmethod
    def _extract_from_dict(cls, payload: dict) -> ScaffoldingOrder:
        issue = payload.get("issue", {})
        fields = issue.get("fields", {})
        issue_key = issue.get("key", "UNKNOWN")
        description = fields.get("description", "")
        
        logger.info(f"Processing Task {issue_key}. Raw Description: {repr(description)}")

        return ScaffoldingOrder(
            issue_key=issue_key,
            raw_instruction=description,
            summary=fields.get("summary", "No Summary"),
            reporter=payload.get("user", {}).get("displayName", "Unknown")
        )
