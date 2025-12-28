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
        
        response = self.client.post(f"rest/api/3/issue/{issue_key}/comment", payload)
        response.raise_for_status()
        return response.json()

    def transition_issue(self, issue_key: str, transition_id: str) -> None:
        # Note: The argument is named 'transition_id' to match the interface, 
        # but the implementation supports searching by name/keyword as per original requirements.
        target_status_keyword = transition_id
        
        # 1. Get available transitions
        response = self.client.get(f"rest/api/3/issue/{issue_key}/transitions")
        response.raise_for_status()
        transitions = response.json().get("transitions", [])

        # 2. Find target ID
        final_id = None
        keyword_lower = target_status_keyword.lower()
        
        for t in transitions:
            t_name = t["name"].lower()
            t_to = t["to"]["name"].lower()
            if keyword_lower in t_name or keyword_lower in t_to:
                final_id = t["id"]
                break
        
        if not final_id:
            # If input was already an ID, we might try to use it directly, 
            # but simplest is to log warning as per original client
            logger.warning(f"No transition found containing '{target_status_keyword}' for issue {issue_key}")
            return

        logger.info(f"Transitioning issue {issue_key} to (ID: {final_id})")
        payload = {
            "transition": {
                "id": final_id
            }
        }
        resp = self.client.post(f"rest/api/3/issue/{issue_key}/transitions", payload)
        resp.raise_for_status()
