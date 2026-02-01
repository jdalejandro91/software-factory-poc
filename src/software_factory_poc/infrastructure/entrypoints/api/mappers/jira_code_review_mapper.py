import re
import logging
import yaml
from typing import Dict, Any

from software_factory_poc.application.core.agents.code_reviewer.value_objects.code_review_order import (
    CodeReviewOrder,
)
from software_factory_poc.infrastructure.entrypoints.api.dtos.jira_webhook_dto import (
    JiraWebhookDTO,
)

logger = logging.getLogger(__name__)


class JiraCodeReviewMapper:
    """
    Maps incoming Jira Webhooks to Domain CodeReviewOrders.
    Extracts automation state injected by ScaffoldingAgent from the task description.
    """

    @staticmethod
    def map_from_webhook(payload: JiraWebhookDTO) -> CodeReviewOrder:
        issue = payload.issue
        if not issue.fields or not issue.fields.description:
            raise ValueError(f"Issue {issue.key} has no description. Cannot parse automation state.")

        # 1. Clean and Parse YAML from Description
        automation_data = JiraCodeReviewMapper._extract_automation_state(issue.fields.description)

        # 2. Extract Mandatory Fields
        try:
            project_id = automation_data["gitlab_project_id"]
            if not isinstance(project_id, int):
                raise ValueError("gitlab_project_id must be an integer")
                
            mr_url = automation_data["review_request_url"]
            source_branch = automation_data["source_branch_name"]
        except KeyError as e:
            raise ValueError(f"Missing critical automation metadata field: {e}. Scaffolding task may be incomplete.")

        # 3. Extract MR IID from URL
        mr_id = JiraCodeReviewMapper._extract_mr_id(mr_url)

        # 4. Construct Order
        return CodeReviewOrder(
            issue_key=issue.key,
            project_id=project_id,
            mr_id=mr_id,
            source_branch=source_branch,
            vcs_provider="GITLAB",
            summary=issue.fields.summary or "Code Review Request",
            description=issue.fields.description,
            mr_url=mr_url,
            requesting_user=payload.user.name if payload.user else None,
        )

    @staticmethod
    def _extract_automation_state(description: str) -> Dict[str, Any]:
        """
        Finds the YAML block in the description and parses it.
        """
        # Regex to find ```yaml ... ``` blocks
        yaml_pattern = re.compile(r"```yaml\s+(.*?)\s+```", re.DOTALL)
        matches = yaml_pattern.findall(description)

        if not matches:
            raise ValueError("No YAML automation state block found in description.")

        # We assume the LAST block is the automation result, or we look for specific keys.
        # Ideally, we look for "automation_result" key in the parsed YAML.
        for match in matches:
            try:
                # Remove common markdown cruft if present inside the block
                clean_yaml = match.replace("{code}", "").strip()
                data = yaml.safe_load(clean_yaml)
                
                if data and "automation_result" in data:
                    return data["automation_result"]
            except yaml.YAMLError:
                logger.warning("Found a YAML block but failed to parse it. Continuing search.")
                continue

        raise ValueError("Could not find valid 'automation_result' block in description YAML.")

    @staticmethod
    def _extract_mr_id(mr_url: str) -> str:
        # Expected format: .../merge_requests/123...
        match = re.search(r"/merge_requests/(\d+)", mr_url)
        if not match:
            raise ValueError(f"Could not extract MR ID from URL: {mr_url}")
        return match.group(1)
