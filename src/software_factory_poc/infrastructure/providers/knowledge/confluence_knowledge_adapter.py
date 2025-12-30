from typing import Any

from software_factory_poc.application.core.domain.exceptions.provider_error import ProviderError
from software_factory_poc.application.core.domain.configuration.knowledge_provider_type import KnowledgeProviderType
from software_factory_poc.application.core.ports.gateways.knowledge_gateway import KnowledgeGateway
from software_factory_poc.infrastructure.providers.knowledge.clients.confluence_http_client import (
    ConfluenceHttpClient,
)
from software_factory_poc.infrastructure.observability.logger_factory_service import LoggerFactoryService

logger = LoggerFactoryService.build_logger(__name__)


class ConfluenceKnowledgeAdapter(KnowledgeGateway):
    """
    Adapter to retrieve knowledge from Confluence.
    """
    def __init__(self, http_client: ConfluenceHttpClient):
        self.http_client = http_client

    def retrieve_context(self, criteria: dict) -> str:
        """
        Retrieves Confluence page content based on structured criteria.
        Supported keys: 'page_id', 'query'.
        """
        try:
            if not criteria:
                raise ValueError("No search criteria provided")

            page_id = criteria.get("page_id")
            text_query = criteria.get("query")

            if page_id:
                return self._get_page_by_id(page_id)
            elif text_query:
                return self._search_pages(text_query)
            else:
                logger.warning(f"No knowledge found for criteria: {criteria}")
                return ""
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
        logger.info(f"Analyzing Confluence response type: {type(page_obj)}")

        if not page_obj: 
            return ""
        
        # Si es lista (resultado de búsqueda), tomar el primero
        if isinstance(page_obj, list) and len(page_obj) > 0:
            page_obj = page_obj[0]
        
        if not isinstance(page_obj, dict):
            return str(page_obj)

        # Rutas posibles en orden de preferencia (Storage es mejor para LLM)
        candidates = [
            ["body", "storage", "value"],  # Formato crudo
            ["body", "view", "value"],     # Formato HTML renderizado
            ["body", "editor", "value"],   # Formato editor (a veces)
            ["excerpt"]                    # Resumen si todo falla
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
                logger.info(f"--- [DEBUG] Content extracted via path: {'.'.join(path)}")
                logger.info(f"🔎 [INFRA:CONFLUENCE] Text extracted (Length: {len(val)}). Preview: {val[:200]!r}...")
                return val

        # Si llegamos aquí, falló la extracción inteligente.
        # Imprimimos el objeto crudo para debug (limitado a 1000 chars)
        raw_preview = str(page_obj)[:1000]
        logger.warning(f"⚠️ CONFLUENCE EXTRACTION FAILED. Raw response preview: {raw_preview}")
        
        # Retornamos string del objeto como fallback de última instancia
        return str(page_obj)
