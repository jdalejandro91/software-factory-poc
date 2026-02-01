import re
from typing import Dict, Any, Optional

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
    def to_order(payload: JiraWebhookDTO) -> CodeReviewOrder:
        desc = payload.issue.fields.description
        if not desc:
            raise ValueError("Description missing in webhook payload")
        
        try:
            # 1. Extract context
            data = JiraCodeReviewMapper._extract_automation_context(desc)
            if not data:
                raise ValueError("Extracted automation context is empty")

            # 2. Build Order
            # Ensure project_id is int
            pid = data.get("gitlab_project_id")
            if not pid:
                raise ValueError("Missing 'gitlab_project_id' in automation context")
                
            mr_url = data.get("review_request_url", "")
            if not mr_url:
                raise ValueError("Missing 'review_request_url' in automation context")

            return CodeReviewOrder(
                issue_key=payload.issue.key, 
                project_id=int(pid),
                mr_id=JiraCodeReviewMapper._extract_mr_id(mr_url),
                source_branch=data.get("source_branch_name", "unknown"),
                vcs_provider="GITLAB",
                summary=payload.issue.fields.summary or "Code Review Task", 
                description=desc,
                mr_url=mr_url, 
                requesting_user=payload.user.name if payload.user else None
            )
        except (KeyError, ValueError, TypeError) as e: 
             # Use a safe fallback for logging data if it was partially extracted
             safe_data = locals().get("data", "Not Extracted")
             logger.error(f"Mapping failed for {payload.issue.key}: {e}. Data extracted: {safe_data}")
             raise ValueError(f"Mapping failed: {e}. Ensure Scaffolding completed successfully.")

    @staticmethod
    def _extract_automation_context(description: str) -> Dict[str, Any]:
        """
        Robustly finds the Automation Context searching for 'code_review_params'.
        """
        # 1. Find ANY code block with 'yaml' hint or just generically
        code_block_iter = re.finditer(r"```(?:yaml)?\s*([\s\S]*?)\s*```", description, re.DOTALL | re.IGNORECASE)
        
        for match in code_block_iter:
            raw_yaml = match.group(1).strip()
            try:
                parsed = yaml.safe_load(raw_yaml)
                if isinstance(parsed, dict):
                    # TARGET: Check for 'code_review_params' key
                    if "code_review_params" in parsed and isinstance(parsed["code_review_params"], dict):
                        return parsed["code_review_params"]
                    
                    # Fallback: Maybe the block IS the params directly (legacy or manual edit)
                    if "gitlab_project_id" in parsed:
                        return parsed
                        
            except yaml.YAMLError:
                continue

        # 2. Fallback: Jira {code} style
        jira_match = re.search(r"\{code(?::yaml)?\}\s*([\s\S]*?)\s*\{code\}", description, re.DOTALL | re.IGNORECASE)
        if jira_match:
            try:
                parsed = yaml.safe_load(jira_match.group(1).strip())
                if isinstance(parsed, dict) and "code_review_params" in parsed:
                    return parsed["code_review_params"]
            except yaml.YAMLError:
                pass

        logger.warning("YAML parsing failed or 'code_review_params' not found. Attempting regex fallback.")
        return JiraCodeReviewMapper._extract_via_regex(description)

    @staticmethod
    def _extract_via_regex(text: str) -> Dict[str, Any]:
        """Manual regex fallback for broken YAML."""
        context = {}
        
        # Project ID
        pid_match = re.search(r"gitlab_project_id:\s*['\"]?(\d+)['\"]?", text)
        if pid_match:
            context["gitlab_project_id"] = pid_match.group(1)
            
        # Review URL
        url_match = re.search(r"review_request_url:\s*['\"]?(https?://[^\s\"']+)['\"]?", text)
        if url_match:
            context["review_request_url"] = url_match.group(1)
            
        # Source Branch
        branch_match = re.search(r"source_branch_name:\s*['\"]?([^\s\"']+)['\"]?", text)
        if branch_match:
            context["source_branch_name"] = branch_match.group(1)

        if "gitlab_project_id" not in context:
            # If we strictly can't find ID, we can't proceed.
            logger.error("Regex extraction failed to find gitlab_project_id")
            return {}
            
        return context

    @staticmethod
    def _extract_mr_id(mr_url: str) -> str:
        # Supports /merge_requests/123 or /pull/123
        match = re.search(r"/(?:merge_requests|pull)/(\d+)", mr_url)
        if not match:
            # If standard pattern fails, return '0' or raise? 
            # Raising is better to stop early.
            raise ValueError(f"Could not extract MR ID from URL: {mr_url}")
        return match.group(1)
