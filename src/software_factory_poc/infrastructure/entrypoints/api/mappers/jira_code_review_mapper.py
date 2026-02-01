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
             logger.error(f"Mapping failed for {payload.issue.key}: {e}")
             raise ValueError(f"Mapping failed: {e}. Ensure Scaffolding completed successfully.")

    @staticmethod
    def _extract_automation_context(description: str) -> Dict[str, Any]:
        """
        Robustly finds the Automation Context.
        Strategy: Find the YAML code block, parse it fully, and look for 'code_review_params' inside.
        """
        # 1. Find ANY code block with 'yaml' hint or just generically
        # This matches ```yaml ... ``` or {code:yaml} ... {code}
        code_block_pattern = re.compile(r"```(?:yaml)?\s*([\s\S]*?)\s*```", re.DOTALL | re.IGNORECASE)
        match = code_block_pattern.search(description)
        
        if not match:
            # Try Jira style
            jira_pattern = re.compile(r"\{code(?::yaml)?\}\s*([\s\S]*?)\s*\{code\}", re.DOTALL | re.IGNORECASE)
            match = jira_pattern.search(description)

        if not match:
            # Last resort: Try finding the keys directly in the text without block (fallback)
            return JiraCodeReviewMapper._extract_via_regex(description)

        raw_yaml = match.group(1).strip()
        
        try:
            # 2. Parse the whole block
            parsed = yaml.safe_load(raw_yaml)
            if not isinstance(parsed, dict):
                logger.warning("Parsed YAML is not a dict, trying regex fallback.")
                return JiraCodeReviewMapper._extract_via_regex(description)
            
            # 3. Locate the params
            # Case A: Nested under code_review_params (Unified Block)
            if "code_review_params" in parsed and isinstance(parsed["code_review_params"], dict):
                return parsed["code_review_params"]
            
            # Case B: Flat structure (Legacy or different format)
            if "gitlab_project_id" in parsed:
                return parsed
                
            # Case C: Not found in this block? Might be multiple blocks. 
            # Ideally iterate all blocks, but for now fallback to regex.
            
        except yaml.YAMLError as e:
            logger.warning(f"YAML parsing failed: {e}. Trying regex fallback.")
            
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
