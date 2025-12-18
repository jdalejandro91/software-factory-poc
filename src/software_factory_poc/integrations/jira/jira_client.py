import base64
from typing import Any, Dict

import httpx

from software_factory_poc.config.settings_pydantic import Settings, JiraAuthMode
from software_factory_poc.observability.logger_factory_service import build_logger

logger = build_logger(__name__)


class JiraClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.base_url = settings.jira_base_url.rstrip("/")
        self._validate_config()

    def _validate_config(self):
        # Ensure we have credentials for the chosen mode
        self.settings.validate_jira_credentials()

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        mode = self.settings.jira_auth_mode
        
        if mode == JiraAuthMode.CLOUD_API_TOKEN:
            email = self.settings.jira_user_email
            token = self.settings.jira_api_token.get_secret_value() if self.settings.jira_api_token else ""
            creds = f"{email}:{token}"
            encoded = base64.b64encode(creds.encode("utf-8")).decode("utf-8")
            headers["Authorization"] = f"Basic {encoded}"

        elif mode == JiraAuthMode.BASIC:
             # Assuming Basic uses api_token as password logic if user_email is not present
             # Or if user provided explicit basic auth string?
             # For PoC, let's treat Basic similar to Cloud but maybe just token?
             # Standard Basic Auth is user:pass.
             # Let's reuse email:token logic for Basic as fallback or handle purely token.
             # If user_email is present, use it.
             email = self.settings.jira_user_email or ""
             token = self.settings.jira_api_token.get_secret_value() if self.settings.jira_api_token else ""
             creds = f"{email}:{token}"
             encoded = base64.b64encode(creds.encode("utf-8")).decode("utf-8")
             headers["Authorization"] = f"Basic {encoded}"

        elif mode == JiraAuthMode.BEARER:
            token = self.settings.jira_bearer_token.get_secret_value() if self.settings.jira_bearer_token else ""
            headers["Authorization"] = f"Bearer {token}"

        return headers

    def get_issue(self, issue_key: str) -> Dict[str, Any]:
        """
        Fetches an issue by key.
        """
        url = f"{self.base_url}/rest/api/3/issue/{issue_key}"
        logger.info(f"Fetching Jira issue: {url}")
        
        with httpx.Client() as client:
            response = client.get(url, headers=self._get_headers(), timeout=10.0)
            response.raise_for_status()
            return response.json()

    def add_comment(self, issue_key: str, body: str) -> Dict[str, Any]:
        """
        Adds a comment to an issue.
        Attempts to use ADF (Atlassian Document Format) first if needed, 
        or simple string if API supports 'body'.
        Jira Cloud v3 API often requires ADF for comments.
        We will construct a minimal ADF paragraph.
        """
        url = f"{self.base_url}/rest/api/3/issue/{issue_key}/comment"
        logger.info(f"Adding comment to Jira issue: {issue_key}")

        # Minimal ADF
        adf_payload = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "text": body,
                                "type": "text"
                            }
                        ]
                    }
                ]
            }
        }
        
        with httpx.Client() as client:
            response = client.post(url, headers=self._get_headers(), json=adf_payload, timeout=10.0)
            response.raise_for_status()
            return response.json()
