import re

from software_factory_poc.core.application.skills.review.prompt_templates import (
    CodeReviewOrder,
)
from software_factory_poc.infrastructure.entrypoints.api.dtos.jira_webhook_dto import (
    JiraWebhookDTO,
)

# Reuse the robust extraction logic from the main payload mapper
from software_factory_poc.infrastructure.entrypoints.api.mappers.jira_payload_mapper import (
    JiraPayloadMapper,
)
from software_factory_poc.infrastructure.observability.logger_factory_service import (
    LoggerFactoryService,
)

logger = LoggerFactoryService.build_logger(__name__)


class JiraCodeReviewMapper:
    """
    Maps incoming Jira Webhooks to Domain CodeReviewOrders.
    Extracts automation state (code_review_params) from the task description.
    """

    @staticmethod
    def to_order(payload: JiraWebhookDTO) -> CodeReviewOrder:
        fields = payload.issue.fields
        if fields is None:
            raise ValueError("Fields missing in webhook payload")
        desc = fields.description
        if not desc:
            raise ValueError("Description missing in webhook payload")

        try:
            # 1. Parse Description using the Robust Logic from JiraPayloadMapper
            # This ensures we respect the {code:yaml} and ```yaml blocks correctly
            task_desc = JiraPayloadMapper._parse_description_config(desc)
            config = task_desc.config

            # 2. Extract context
            # Look for nested 'code_review_params', fallback to root
            data = config.get("code_review_params")
            if not data:
                # Compatibility Fallback: check if root has keys
                if config.get("gitlab_project_id"):
                    data = config

            if not data:
                raise ValueError(
                    "Extracted automation context (code_review_params) is empty or not found"
                )

            # 3. Extract Fields safely
            pid = data.get("gitlab_project_id")
            if not pid:
                raise ValueError("Missing 'gitlab_project_id'")

            mr_url = data.get("review_request_url", "")
            # Support both keys just in case
            source_branch = data.get("source_branch_name") or data.get("source_branch", "unknown")

            return CodeReviewOrder(
                issue_key=payload.issue.key,
                project_id=int(pid),
                mr_id=JiraCodeReviewMapper._extract_mr_id(mr_url),
                source_branch=source_branch,
                vcs_provider="GITLAB",
                summary=fields.summary or "Code Review Task",
                description=desc,
                mr_url=mr_url,
                requesting_user=payload.user.name if payload.user else None,
            )
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Mapping failed for {payload.issue.key}: {e}")
            raise ValueError(f"Mapping failed: {e}") from e

    @staticmethod
    def _extract_mr_id(mr_url: str) -> str:
        if not mr_url:
            return "0"
        match = re.search(r"/(?:merge_requests|pull)/(\d+)", mr_url)
        return match.group(1) if match else "0"
