import base64
from typing import Any, Dict, Union

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
        url = f"{self.base_url}/rest/api/3/issue/{issue_key}"
        logger.info(f"Fetching Jira issue: {url}")
        
        with httpx.Client() as client:
            response = client.get(url, headers=self._get_headers(), timeout=10.0)
            response.raise_for_status()
            return response.json()

    def add_comment(self, issue_key: str, content: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Agrega un comentario. Soporta ADF nativo (Dict) o texto simple (str).
        """
        url = f"{self.base_url}/rest/api/3/issue/{issue_key}/comment"
        logger.info(f"Adding comment to Jira issue: {issue_key}")

        payload = {}
        
        # Si recibimos un Diccionario, asumimos que es un documento ADF bien formado
        if isinstance(content, dict):
            payload = {"body": content}
        else:
            # Fallback para texto simple (lo envolvemos en un párrafo básico)
            payload = {
                "body": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": str(content)}]
                        }
                    ]
                }
            }
        
        with httpx.Client() as client:
            response = client.post(url, headers=self._get_headers(), json=payload, timeout=10.0)
            response.raise_for_status()
            return response.json()
