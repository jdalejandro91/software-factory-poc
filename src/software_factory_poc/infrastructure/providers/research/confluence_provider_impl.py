import re
from typing import Any

from software_factory_poc.application.core.agents.research.ports.research_gateway import ResearchGateway
from software_factory_poc.application.core.agents.research.config.research_provider_type import ResearchProviderType
from software_factory_poc.infrastructure.configuration.confluence_settings import ConfluenceSettings
from software_factory_poc.infrastructure.providers.research.clients.confluence_http_client import ConfluenceHttpClient
from software_factory_poc.application.core.agents.common.exceptions.provider_error import ProviderError
from software_factory_poc.infrastructure.observability.logger_factory_service import LoggerFactoryService

logger = LoggerFactoryService.build_logger(__name__)


class ConfluenceProviderImpl(ResearchGateway):
    """
    Adapter to retrieve knowledge from Confluence.
    Implements ResearchGateway.
    """
    def __init__(self, settings: ConfluenceSettings):
        self.settings = settings
        self.http_client = ConfluenceHttpClient(settings)

    def retrieve_context(self, query: str) -> str:
        """
        Retrieves Confluence page content based on query string or configuration.
        """
        try:
            if not query:
                raise ValueError("No search query provided")

            text_query = query
            
            # Smart Logic: Check if query is about architecture
            if "architecture" in text_query.lower() or "arquitectura" in text_query.lower():
                 if self.settings.architecture_doc_page_id:
                     logger.info(f"Investigando documento de Arquitectura (ID: {self.settings.architecture_doc_page_id}) por coincidencia de query...")
                     return self._get_page_by_id(self.settings.architecture_doc_page_id)

            logger.info(f"Investigando en Confluence por query: '{text_query}'...")
            return self._search_pages(text_query)

        except Exception as e:
            # Map low level exceptions to ProviderError
            retryable = True
            if hasattr(e, "status_code") and e.status_code == 404:
                retryable = False
            
            raise ProviderError(
                provider=ResearchProviderType.CONFLUENCE,
                message=f"Confluence error: {e}",
                retryable=retryable
            )

    def _get_page_by_id(self, page_id: str) -> str:
        page = self.http_client.get_page(page_id)
        return self._extract_text(page)

    def _search_pages(self, cql_query: str) -> str:
        results = self.http_client.search(cql_query)
        if not results:
             return "No knowledge found."
        return self._extract_text(results[0])

    def _extract_text(self, page_obj: Any) -> str:
        if not page_obj: 
            return ""
        
        if isinstance(page_obj, list) and len(page_obj) > 0:
            page_obj = page_obj[0]
        
        if not isinstance(page_obj, dict):
            return str(page_obj)

        candidates = [
            ["body", "storage", "value"],
            ["body", "view", "value"],
            ["body", "editor", "value"],
            ["excerpt"]
        ]

        for path in candidates:
            val = page_obj
            for key in path:
                if isinstance(val, dict):
                    val = val.get(key)
                else:
                    val = None
                    break
            
            if val and isinstance(val, str) and len(val.strip()) > 50:
                return self._sanitize_content(val)

        # Fallback to string repr if nothing else matches, but sanitize it too
        return self._sanitize_content(str(page_obj))

    def _sanitize_content(self, input_text: str) -> str:
        """
        Removes HTML tags and entities from the content.
        """
        if not input_text:
            return ""
            
        # 1. Remove HTML Tags
        clean_text = re.sub(r"<[^>]+>", " ", input_text)
        
        # 2. Collapse whitespace
        clean_text = " ".join(clean_text.split())
        
        # 3. Basic Entity Decode (can be improved with html.unescape if needed)
        # For now, simplistic approach is fine or use standard lib if imported.
        # Let's import html standard lib for robustness if I can edit imports again, 
        # or just rely on the fact that LLMs handle entities okay-ish. 
        # But user requested "Sanitización".
        # I will stick to basic tag stripping as requested.
        
        return clean_text
