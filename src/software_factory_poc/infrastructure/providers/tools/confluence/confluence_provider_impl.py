import httpx
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

from software_factory_poc.application.core.exceptions.confluence_error import (
    ConfluenceIntegrationError,
)
from software_factory_poc.application.ports.tools.confluence_provider import ConfluenceProvider
from software_factory_poc.infrastructure.providers.tools.confluence.clients.confluence_http_client import (
    ConfluenceHttpClient,
)


class ConfluenceProviderImpl(ConfluenceProvider):
    def __init__(self, http_client: ConfluenceHttpClient):
        self.client = http_client

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_page_content(self, page_id: str) -> str:
        try:
            response = self.client.get(f"rest/api/content/{page_id}", params={"expand": "body.storage"})
            
            if response.status_code == 401:
                raise ConfluenceIntegrationError("Unauthorized: Check Confluence credentials.")
            if response.status_code == 403:
                raise ConfluenceIntegrationError("Forbidden: Access denied to Confluence page.")
            if response.status_code == 404:
                raise ConfluenceIntegrationError(f"Confluence page {page_id} not found.")
                
            response.raise_for_status()
            data = response.json()
            
            try:
                raw_html = data["body"]["storage"]["value"]
            except KeyError as e:
                raise ConfluenceIntegrationError(f"Unexpected response structure for page {page_id}") from e
            
            return self._clean_html(raw_html)
            
        except httpx.RequestError as e:
            raise ConfluenceIntegrationError(f"Network error connecting to Confluence: {str(e)}") from e
        except httpx.HTTPStatusError as e:
             raise ConfluenceIntegrationError(f"HTTP error {e.response.status_code} from Confluence: {str(e)}") from e

    def _clean_html(self, html_content: str) -> str:
        if not html_content:
            return ""
        soup = BeautifulSoup(html_content, "html.parser")
        text = soup.get_text(separator="\n")
        
        # Eliminar saltos de línea excesivos
        import re
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()
