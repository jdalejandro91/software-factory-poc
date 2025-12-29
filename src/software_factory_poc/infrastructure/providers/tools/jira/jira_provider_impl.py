from typing import Any

from software_factory_poc.application.ports.tools.jira_provider import JiraProvider
from software_factory_poc.infrastructure.providers.tools.jira.clients.jira_http_client import (
    JiraHttpClient,
)
from software_factory_poc.infrastructure.observability.logger_factory_service import build_logger

logger = build_logger(__name__)


class JiraProviderImpl(JiraProvider):
    def __init__(self, http_client: JiraHttpClient):
        self.client = http_client

    def get_issue(self, issue_key: str) -> dict[str, Any]:
        logger.info(f"Fetching Jira issue: {issue_key}")
        response = self.client.get(f"rest/api/3/issue/{issue_key}")
        response.raise_for_status()
        return response.json()

    def add_comment(self, issue_key: str, body: Any) -> dict[str, Any]:
        logger.info(f"Adding comment to Jira issue: {issue_key}")
        
        payload = {}
        if isinstance(body, dict):
            payload = {"body": body}
        else:
            # Helper for simple text to ADF, can be extracted to mapper if needed but simple enough here
            payload = {
                "body": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": str(body)}]
                        }
                    ]
                }
            }
        
        logger.debug(f"Sending comment payload to Jira: {payload}")
        response = self.client.post(f"rest/api/3/issue/{issue_key}/comment", payload)
        response.raise_for_status()
        return response.json()

    def transition_issue(self, issue_key: str, transition_id: str) -> None:
        # Note: The argument is named 'transition_id' to match the interface, 
        # but the implementation supports searching by name/keyword as per original requirements.
        target_status_keyword = transition_id
        
        # 1. Get available transitions
        response = self.client.get(f"rest/api/3/issue/{issue_key}/transitions")
        try:
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to fetch transitions for {issue_key}: {e}")
            raise e
            
        transitions = response.json().get("transitions", [])
        
        available_names = [t["name"] for t in transitions]
        logger.debug(f"Transiciones disponibles para {issue_key}: {available_names}")

        # 2. Find target ID with enhanced logic
        final_id = None
        keyword_lower = target_status_keyword.lower()
        
        # Strategy A: Exact Match (Case Insensitive)
        for t in transitions:
            if t["name"].lower() == keyword_lower:
                final_id = t["id"]
                logger.info(f"Transition '{target_status_keyword}' found (Exact Match ID: {final_id})")
                break
        
        # Strategy B: Partial Match (if no exact found)
        if not final_id:
            for t in transitions:
                if keyword_lower in t["name"].lower() or keyword_lower in t["to"]["name"].lower():
                    final_id = t["id"]
                    logger.info(f"Transition '{target_status_keyword}' found (Partial Match ID: {final_id})")
                    break
        
        if not final_id:
            error_msg = f"Transition '{target_status_keyword}' not found. Available: {available_names}"
            logger.error(error_msg)
            # Importing here to avoid circular dependencies if any at module level
            from software_factory_poc.application.core.exceptions.provider_error import ProviderError
            from software_factory_poc.application.core.value_objects.provider_name import ProviderName
            
            raise ProviderError(
                provider=ProviderName.JIRA,
                message=error_msg,
                retryable=True  # Jira might be slow or just need a retry? Or maybe config error.
            )

        logger.info(f"Transitioning issue {issue_key} to (ID: {final_id})")
        payload = {
            "transition": {
                "id": final_id
            }
        }
        resp = self.client.post(f"rest/api/3/issue/{issue_key}/transitions", payload)
        resp.raise_for_status()
