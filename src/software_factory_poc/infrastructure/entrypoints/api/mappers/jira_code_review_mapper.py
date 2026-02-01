import re
from typing import Dict, Any

import yaml

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
    def map_from_webhook(payload: JiraWebhookDTO) -> CodeReviewOrder:
        """
        Maps the webhook payload to a domain order.
        Alias for to_order to maintain compatibility with existing router call sites.
        """
        return JiraCodeReviewMapper.to_order(payload)

    @staticmethod
    def to_order(payload: JiraWebhookDTO) -> CodeReviewOrder:
        if not (desc := payload.issue.fields.description): raise ValueError("Description missing in webhook payload")
        
        try:
            data = JiraCodeReviewMapper._extract_automation_context(desc)
            return CodeReviewOrder(
                issue_key=payload.issue.key, 
                project_id=int(data["gitlab_project_id"]),
                mr_id=JiraCodeReviewMapper._extract_mr_id(data["review_request_url"]),
                source_branch=data["source_branch_name"], 
                vcs_provider="GITLAB",
                summary=payload.issue.fields.summary or "Code Review Task", 
                description=desc,
                mr_url=data["review_request_url"], 
                requesting_user=payload.user.name if payload.user else None
            )
        except (KeyError, ValueError) as e: 
             # Fallback logic could go here if requested, but prompt said "If block exists, trust it 100%".
             # Exception raised corresponds to "Automation state corrupted or missing".
             raise ValueError(f"Mapping failed: {e}. Ensure Scaffolding completed successfully.")

    @staticmethod
    def _extract_automation_context(description: str) -> Dict[str, Any]:
        """
        Robustly finds the Automation Context in the description.
        Tolerates manual edits, missing tildes, or extra spaces.
        """
        # 1. Broad Lazy Capture
        # Captures everything after "code_review_params:" until the next code block or EOF
        # Tolerates missing indentation or extra newlines
        yaml_pattern = re.compile(r"code_review_params:\s*\n+([\s\S]*?)(?=```|$)", re.MULTILINE)
        match = yaml_pattern.search(description)

        if not match:
             # Last resort fallback: try to find the old full-block format
             fallback_pattern = re.compile(r"```yaml\s+(.*?)\s+```", re.DOTALL)
             match = fallback_pattern.search(description)
             if not match:
                 raise ValueError("Automation state corrupted or missing ('code_review_params' block not found)")

        raw_content = match.group(1).replace("{code}", "").strip()
        
        try:
            # 2. Attempt YAML Parse (Preferred)
            # We reconstruct the dict wrapper to be safe
            full_yaml_str = f"code_review_params:\n{raw_content}"
            data = yaml.safe_load(full_yaml_str)
            
            if data and isinstance(data, dict) and "code_review_params" in data:
                return data["code_review_params"]
            
        except yaml.YAMLError:
            logger.warning("YAML parsing failed for automation context. Attempting manual regex extraction.")

        # 3. Manual Regex Fallback (Fail-Safe)
        # If the YAML is broken (e.g. wrong indentation), we grep the values directly.
        context = {}
        
        # Project ID
        pid_match = re.search(r"gitlab_project_id:\s*(\d+)", raw_content)
        if pid_match:
            context["gitlab_project_id"] = int(pid_match.group(1))
            
        # Review URL
        url_match = re.search(r"review_request_url:\s*[\"']?([^\s\"']+)[\"']?", raw_content)
        if url_match:
            context["review_request_url"] = url_match.group(1)
            
        # Source Branch
        branch_match = re.search(r"source_branch_name:\s*[\"']?([^\s\"']+)[\"']?", raw_content)
        if branch_match:
            context["source_branch_name"] = branch_match.group(1)
            
        # Validate critical fields
        if "gitlab_project_id" in context and "review_request_url" in context:
            return context
            
        raise ValueError("Critical automation fields missing. YAML invalid and manual fallback failed.")

    @staticmethod
    def _extract_mr_id(mr_url: str) -> str:
        match = re.search(r"/merge_requests/(\d+)", mr_url)
        if not match:
            raise ValueError(f"Could not extract MR ID from URL: {mr_url}")
        return match.group(1)
