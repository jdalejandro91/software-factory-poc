from typing import Any

from software_factory_poc.application.core.domain.exceptions.provider_error import ProviderError
from software_factory_poc.application.core.domain.configuration.knowledge_provider_type import KnowledgeProviderType
from software_factory_poc.application.core.ports.gateways.knowledge_gateway import KnowledgeGateway
from software_factory_poc.infrastructure.providers.knowledge.clients.confluence_http_client import (
    ConfluenceHttpClient,
)


class ConfluenceKnowledgeAdapter(KnowledgeGateway):
    """
    Adapter to retrieve knowledge from Confluence.
    """
    def __init__(self, http_client: ConfluenceHttpClient):
        self.http_client = http_client

    def retrieve_context(self, query: str) -> str:
        """
        Retrieves Confluence page content.
        Query can be a Page ID or a generic search query (simplified for this PoC).
        Assumption: If query is numeric, it's an ID. Otherwise search.
        """
        try:
            query = query.strip()
            if query.isdigit():
                return self._get_page_by_id(query)
            else:
                return self._search_pages(query)
        except Exception as e:
            # Map low level exceptions to ProviderError
            if hasattr(e, "status_code") and e.status_code == 404:
                retryable = False
            else:
                retryable = True # Assume network/server errors are retryable
            
            raise ProviderError(
                provider=KnowledgeProviderType.CONFLUENCE,
                message=f"Confluence error: {e}",
                retryable=retryable
            )

    def _get_page_by_id(self, page_id: str) -> str:
        # Assuming http_client has a method for this or we call raw generic method
        # Checking existing ConfluenceHttpClient... if not capable, we assume generic 'get'
        # For PoC, let's assume get_page matches our needs
        page = self.http_client.get_page(page_id)
        # Extract storage or body
        # Usually: page['body']['storage']['value'] or similar
        return self._extract_text(page)

    def _search_pages(self, cql_query: str) -> str:
        # Simplified: return first match?
        results = self.http_client.search(cql_query)
        if not results:
             return "No knowledge found."
        # Aggregate logic? Or just first.
        return self._extract_text(results[0])

    def _extract_text(self, page_obj: Any) -> str:
        # Helper to safely extract text from Confluence JSON response
        try:
            # Handle List results (from Search)
            if isinstance(page_obj, list):
                if not page_obj:
                    return "No content in list."
                # Take first result
                page_obj = page_obj[0]

            if not isinstance(page_obj, dict):
                 return str(page_obj)

            # Check structure based on common Atlassian API
            # Expected: { "body": { "storage": { "value": "<html>...</html>" } } }
            body = page_obj.get("body")
            if not body:
                # Log debug, might be a summary object without body
                # LoggerFactoryService not injected here directly, assuming usage of ProviderError or print for PoC
                # But ideally we should log. Using print for now as logger isn't in __init__
                return str(page_obj)

            storage = body.get("storage")
            if not storage:
                 return str(page_obj)
            
            value = storage.get("value", "")
            return value if value else str(page_obj)
            
        except Exception:
            return str(page_obj) # Fallback to raw JSON string
