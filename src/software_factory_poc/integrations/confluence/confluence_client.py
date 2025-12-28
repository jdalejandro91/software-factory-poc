from __future__ import annotations

import httpx
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

from software_factory_poc.config.settings_pydantic import Settings
from software_factory_poc.core.exceptions.confluence_error import ConfluenceIntegrationError


class ConfluenceClient:
    def __init__(self, settings: Settings) -> None:
        self.base_url = settings.confluence_base_url.rstrip("/")
        self.auth = (
            settings.confluence_user_email,
            settings.confluence_api_token.get_secret_value(),
        )
        self.timeout = 30.0

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_page_content(self, page_id: str) -> str:
        """
        Fetches the content of a Confluence page and returns cleaned text.
        
        Args:
            page_id: The ID of the page to fetch.
            
        Returns:
            Cleaned text content of the page.
            
        Raises:
            ConfluenceIntegrationError: If the API call fails/returns non-200.
        """
        url = f"{self.base_url}/rest/api/content/{page_id}"
        params = {"expand": "body.storage"}
        
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url, auth=self.auth, params=params)
                
                if response.status_code == 401:
                    raise ConfluenceIntegrationError("Unauthorized: Check Confluence credentials.")
                if response.status_code == 403:
                    raise ConfluenceIntegrationError("Forbidden: Access denied to Confluence page.")
                if response.status_code == 404:
                    raise ConfluenceIntegrationError(f"Confluence page {page_id} not found.")
                    
                response.raise_for_status()
                data = response.json()
                
                # Extract HTML
                try:
                    raw_html = data["body"]["storage"]["value"]
                except KeyError:
                    raise ConfluenceIntegrationError(f"Unexpected response structure for page {page_id}")
                
                # Clean HTML
                return self._clean_html(raw_html)
                
        except httpx.RequestError as e:
            raise ConfluenceIntegrationError(f"Network error connecting to Confluence: {str(e)}") from e
        except httpx.HTTPStatusError as e:
             raise ConfluenceIntegrationError(f"HTTP error {e.response.status_code} from Confluence: {str(e)}") from e

    def _clean_html(self, html_content: str) -> str:
        soup = BeautifulSoup(html_content, "html.parser")
        return soup.get_text(separator="\n").strip()
