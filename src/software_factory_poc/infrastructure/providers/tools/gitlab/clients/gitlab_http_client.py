from typing import Any

import httpx

from software_factory_poc.configuration.tools.tool_settings import ToolSettings
from software_factory_poc.infrastructure.observability.logger_factory_service import build_logger

logger = build_logger(__name__)


class GitLabHttpClient:
    def __init__(self, settings: ToolSettings):
        self.settings = settings
        self.base_url = settings.gitlab_base_url.rstrip("/")
        self._validate_config()

    def _validate_config(self):
        self.settings.validate_gitlab_credentials()

    def _get_headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        token = self.settings.gitlab_token.get_secret_value() if self.settings.gitlab_token else ""
        headers["PRIVATE-TOKEN"] = token
        return headers

    def get(self, path: str, params: dict[str, Any] = None) -> httpx.Response:
        url = f"{self.base_url}/{path.lstrip('/')}"
        with httpx.Client() as client:
            return client.get(url, headers=self._get_headers(), params=params, timeout=10.0)

    def post(self, path: str, json_data: dict[str, Any]) -> httpx.Response:
        url = f"{self.base_url}/{path.lstrip('/')}"
        with httpx.Client() as client:
            return client.post(url, headers=self._get_headers(), json=json_data, timeout=20.0)
            
    def head(self, path: str) -> httpx.Response:
        url = f"{self.base_url}/{path.lstrip('/')}"
        with httpx.Client() as client:
            return client.head(url, headers=self._get_headers(), timeout=5.0)
