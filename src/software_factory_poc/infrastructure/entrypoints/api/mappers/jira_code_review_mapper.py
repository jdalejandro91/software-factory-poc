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
    Extracts automation state (code_review_params) from the task description.
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
                raise ValueError("Extracted automation context (code_review_params) is empty")

            # 2. Extract Fields safely
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
                summary=payload.issue.fields.summary or "Code Review Task", 
                description=desc,
                mr_url=mr_url, 
                requesting_user=payload.user.name if payload.user else None
            )
        except (KeyError, ValueError, TypeError) as e: 
             logger.error(f"Mapping failed for {payload.issue.key}: {e}")
             raise ValueError(f"Mapping failed: {e}")

    @staticmethod
    def _extract_automation_context(description: str) -> Dict[str, Any]:
        """
        Scans for YAML blocks and looks for 'code_review_params'.
        """
        # 1. Regex for Code Blocks (Markdown or Jira style)
        # Matches content inside ```yaml ... ``` or {code:yaml} ... {code}
        code_block_iter = re.finditer(r"```(?:yaml)?\s*([\s\S]*?)\s*```", description, re.DOTALL | re.IGNORECASE)
        
        for match in code_block_iter:
            try:
                parsed = yaml.safe_load(match.group(1).strip())
                if isinstance(parsed, dict):
                    # PRIORIDAD 1: Clave exacta
                    if "code_review_params" in parsed:
                        return parsed["code_review_params"]
                    # PRIORIDAD 2: Estructura plana (si el bloque contiene solo los params)
                    if "gitlab_project_id" in parsed:
                        return parsed
            except yaml.YAMLError:
                continue

        # Fallback for Jira {code} format if regex above didn't catch it
        jira_iter = re.finditer(r"\{code(?::yaml)?\}\s*([\s\S]*?)\s*\{code\}", description, re.DOTALL | re.IGNORECASE)
        for match in jira_iter:
             try:
                parsed = yaml.safe_load(match.group(1).strip())
                if isinstance(parsed, dict):
                    if "code_review_params" in parsed:
                        return parsed["code_review_params"]
                    if "gitlab_project_id" in parsed:
                        return parsed
             except yaml.YAMLError:
                pass
        
        logger.warning("No valid YAML block found with 'code_review_params'.")
        return {}

    @staticmethod
    def _extract_mr_id(mr_url: str) -> str:
        if not mr_url: return "0"
        match = re.search(r"/(?:merge_requests|pull)/(\d+)", mr_url)
        return match.group(1) if match else "0"
