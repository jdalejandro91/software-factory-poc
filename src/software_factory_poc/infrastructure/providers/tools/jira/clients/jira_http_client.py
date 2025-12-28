import base64
from typing import Any

import httpx

from software_factory_poc.configuration.tools.tool_settings import JiraAuthMode, ToolSettings
from software_factory_poc.infrastructure.observability.logger_factory_service import build_logger

logger = build_logger(__name__)


class JiraHttpClient:
    def __init__(self, settings: ToolSettings):
        self.settings = settings
        self.base_url = settings.jira_base_url.rstrip("/")
        self._validate_config()

    def _validate_config(self):
        self.settings.validate_jira_credentials()

    def _get_headers(self) -> dict[str, str]:
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

    def get(self, path: str) -> httpx.Response:
        url = f"{self.base_url}/{path.lstrip('/')}"
        with httpx.Client() as client:
            return client.get(url, headers=self._get_headers(), timeout=10.0)

    def post(self, path: str, json_data: dict[str, Any]) -> httpx.Response:
        url = f"{self.base_url}/{path.lstrip('/')}"
        with httpx.Client() as client:
            return client.post(url, headers=self._get_headers(), json=json_data, timeout=10.0)
