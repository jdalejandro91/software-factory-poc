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
        Finds the YAML block in the description and parses it using Regex/YAML.
        """
        # Strict Regex capture between automation_result: and closing block
        # Corresponds to prompt instruction: "Use Regex to capture text between automation_result: and ```"
        yaml_pattern = re.compile(r"automation_result:\s*\n(.*?)(?=```|$)", re.DOTALL)
        match = yaml_pattern.search(description)

        if not match:
             # Try finding the block via the previous method (full yaml block) just in case
             fallback_pattern = re.compile(r"```yaml\s+(.*?)\s+```", re.DOTALL)
             fallback_match = fallback_pattern.search(description)
             if fallback_match:
                 match_content = fallback_match.group(1)
             else:
                 raise ValueError("Automation state corrupted or missing ('automation_result' block not found)")
        else:
             match_content = match.group(1)

        try:
            clean_yaml = match_content.replace("{code}", "").strip()
            # If we captured just the content inside automation_result, parse it directly.
            # However, yaml.safe_load might expect keys. 
            # If the user prompt implies parsing lines manually with regex, we can do that,
            # but yaml.safe_load is more robust if available.
            
            # The capture group (.*?) inside "automation_result:\n(.*?)" essentially captures the indented block.
            # To make it valid YAML to parse, we might need to dedent or just parse it.
            # Let's try parsing the whole block if possible or constructing a wrapper.
            
            # Re-constructing valid yaml for robust parsing:
            full_yaml_str = f"automation_result:\n{clean_yaml}"
            data = yaml.safe_load(full_yaml_str)
            
            if data and "automation_result" in data:
                return data["automation_result"]
            
            # Fallback: return data if it was parsed as flat dict (if capture was perfect)
            if isinstance(data, dict): 
                return data
                
            raise ValueError("Parsed YAML did not result in a dictionary")
            
        except yaml.YAMLError:
             raise ValueError("Extracted block is not valid YAML")

    @staticmethod
    def _extract_mr_id(mr_url: str) -> str:
        match = re.search(r"/merge_requests/(\d+)", mr_url)
        if not match:
            raise ValueError(f"Could not extract MR ID from URL: {mr_url}")
        return match.group(1)
