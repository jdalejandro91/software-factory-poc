import httpx
from software_factory_poc.infrastructure.configuration.tool_settings import ToolSettings


class ConfluenceHttpClient:
    def __init__(self, settings: ToolSettings) -> None:
        self.base_url = settings.confluence_base_url.rstrip("/")
        self.auth = (
            settings.confluence_user_email,
            settings.confluence_api_token.get_secret_value(),
        )
        self.timeout = 30.0

    def get(self, path: str, params: dict = None) -> httpx.Response:
        url = f"{self.base_url}/{path.lstrip('/')}"
        with httpx.Client(timeout=self.timeout) as client:
            return client.get(url, auth=self.auth, params=params)
