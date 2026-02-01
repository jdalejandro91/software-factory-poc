import re
import yaml
from typing import Dict, Any

from software_factory_poc.application.core.agents.code_reviewer.value_objects.code_review_order import (
    CodeReviewOrder,
)
from software_factory_poc.infrastructure.entrypoints.api.dtos.jira_webhook_dto import (
    JiraWebhookDTO,
)
from software_factory_poc.infrastructure.observability.logger_factory_service import (
    LoggerFactoryService,
)

logger = LoggerFactoryService.build_logger(__name__)


class JiraCodeReviewMapper:
    """
    Maps incoming Jira Webhooks to Domain CodeReviewOrders.
    Extracts automation state injected by ScaffoldingAgent from the task description.
    """

    @staticmethod
    @staticmethod
    def map_from_webhook(payload: JiraWebhookDTO) -> CodeReviewOrder:
        if not (desc := payload.issue.fields.description): raise ValueError("Description missing")
        data = JiraCodeReviewMapper._extract_automation_data(desc)
        try:
            return CodeReviewOrder(
                issue_key=payload.issue.key, project_id=int(data["gitlab_project_id"]),
                mr_id=JiraCodeReviewMapper._extract_mr_id(data["review_request_url"]),
                source_branch=data["source_branch_name"], vcs_provider="GITLAB",
                summary=payload.issue.fields.summary or "Code Review", description=desc,
                mr_url=data["review_request_url"], requesting_user=payload.user.name if payload.user else None
            )
        except KeyError: raise ValueError("Automation state corrupted or missing")

    @staticmethod
    def _extract_automation_data(description: str) -> Dict[str, Any]:
        """
        Finds the YAML block in the description and parses it.
        """
        yaml_pattern = re.compile(r"```yaml\s+(.*?)\s+```", re.DOTALL)
        matches = yaml_pattern.findall(description)

        for match in matches:
            try:
                clean_yaml = match.replace("{code}", "").strip()
                data = yaml.safe_load(clean_yaml)
                if data and "automation_result" in data:
                    return data["automation_result"]
            except yaml.YAMLError:
                continue

        raise ValueError("Automation state corrupted or missing ('automation_result' block not found)")

    @staticmethod
    def _extract_mr_id(mr_url: str) -> str:
        match = re.search(r"/merge_requests/(\d+)", mr_url)
        if not match:
            raise ValueError(f"Could not extract MR ID from URL: {mr_url}")
        return match.group(1)
