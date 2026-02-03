import re
from typing import Any

from software_factory_poc.application.core.agents.common.exceptions.provider_error import ProviderError
from software_factory_poc.application.core.agents.research.config.research_provider_type import ResearchProviderType
from software_factory_poc.application.core.agents.research.ports.research_gateway import ResearchGateway
from software_factory_poc.infrastructure.configuration.confluence_settings import ConfluenceSettings
from software_factory_poc.infrastructure.observability.logger_factory_service import LoggerFactoryService
from software_factory_poc.infrastructure.providers.research.clients.confluence_http_client import ConfluenceHttpClient

logger = LoggerFactoryService.build_logger(__name__)


from software_factory_poc.application.core.agents.research.dtos.document_content_dto import DocumentContentDTO
from software_factory_poc.application.core.agents.research.dtos.project_context_dto import ProjectContextDTO

from html.parser import HTMLParser

class _ConfluenceHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text_parts = []
    
    def handle_starttag(self, tag, attrs):
        if tag in ['br', 'p', 'div', 'tr']:
            self.text_parts.append('\n')
        elif tag in ['td', 'th']:
            self.text_parts.append(' | ')
            
    def handle_data(self, data):
        self.text_parts.append(data)
        
    def get_text(self):
        return "".join(self.text_parts).strip()

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
        Retrieves Confluence page content based on query string.
        """
        try:
            if not query:
                raise ValueError("No search query provided")

            logger.info(f"Investigando en Confluence por query: '{query}'...")
            return self._search_pages(query)

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

    def get_page_content(self, page_id: str) -> str:
        """Retrieves content by specific Page ID."""
        try:
            return self._get_page_by_id(page_id)
        except Exception as e:
            if hasattr(e, "status_code") and e.status_code == 404:
                logger.warning(f"Page ID {page_id} not found.")
                return ""
            raise e

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
                parser = _ConfluenceHTMLParser()
                parser.feed(val)
                return self._sanitize_content(parser.get_text())

        # Fallback to string repr if nothing else matches, but sanitize it too
        return self._sanitize_content(str(page_obj))

    def _sanitize_content(self, input_text: str) -> str:
        """
        clean_html: Removes HTML tags and entities from the content.
        Uses regex for tags and manual replacement for common entities as no heavy libs allowed.
        """
        if not input_text:
            return ""

        # 1. Remove HTML Tags (Regex is generally discouraged for HTML but acceptable for stripping tags in simple use cases)
        clean_text = re.sub(r"<[^>]+>", " ", input_text)
        
        # 2. Decode entities (Simplistic)
        # Replacing common ones. If complex, would need html module (import html)
        # Requirement: "Implement Robust HTML cleaning... can use html.unescape"
        # I will import html at method level to avoid top level import issues if any, or rely on standard lib.
        import html
        clean_text = html.unescape(clean_text)

        # 3. Collapse whitespace
        clean_text = " ".join(clean_text.split())

        return clean_text

    def get_project_context(self, project_name: str) -> ProjectContextDTO:
        """
        Retrieves project-specific documentation from Confluence.
        Algorithm:
        1. Find "Projects" folder (Page).
        2. Find project_name child page.
        3. Fetch all children of that project page (with content expanded).
        """
        try:
            logger.info(f"Retrieving Project Context for: '{project_name}'")
            
            # Step 1: Find Root "Projects" Page
            root_results = self.http_client.search('title = "Projects" AND type = "page"')
            if not root_results:
                raise ProviderError(
                    provider=ResearchProviderType.CONFLUENCE,
                    message="Critical: 'Projects' root page not found in Confluence.",
                    retryable=False
                )
            root_id = root_results[0]["id"]
            
            # Step 2: Find Project Page
            # Strategy: Double Try (Exact Match -> Fuzzy Match)
            
            # Attempt 1: Exact Match
            project_cql = f'parent = {root_id} AND title = "{project_name}"'
            logger.info(f"DEBUG CQL (Attempt 1): {project_cql}")
            project_results = self.http_client.search(project_cql)
            
            # Attempt 2: Normalized Match (if needed)
            if not project_results:
                normalized_name = project_name.replace("-", " ").replace("_", " ")
                if normalized_name != project_name:
                    project_cql = f'parent = {root_id} AND title = "{normalized_name}"'
                    logger.info(f"DEBUG CQL (Attempt 2 - Fuzzy): {project_cql}")
                    project_results = self.http_client.search(project_cql)

            if not project_results:
                logger.warning(f"⚠️ Project folder '{project_name}' (or normalized) NOT FOUND in Confluence under parent {root_id}.")
                return ProjectContextDTO(
                    project_name=project_name,
                    root_page_id="N/A",
                    documents=[],
                    total_documents=0
                )
            
            project_page_id = project_results[0]["id"]
            
            # Step 3: Fetch Children with Content (Batch Optimization)
            all_pages = []
            start = 0
            limit = 50
            
            while True:
                results = self.http_client.get_child_pages(
                    page_id=project_page_id, 
                    limit=limit, 
                    expand='body.storage'
                )
                
                if not results:
                    break
                    
                all_pages.extend(results)
                start += limit
                
                # Check pagination via implicit rule: if less than limit returned, no more pages
                # However, the user asked for explicit increment and break on empty results, which is safer
                if len(results) < limit:
                     break
            
            docs = []
            for child in all_pages:
                raw_html = self._extract_text(child) # Reuse extraction logic which uses _ConfluenceHTMLParser
                
                doc = DocumentContentDTO(
                    title=child.get("title", "Untitled"),
                    url=child.get("_links", {}).get("webui", ""),
                    content=raw_html,
                    metadata={
                        "id": child.get("id"),
                        "space": child.get("space", {}).get("key", "")
                    }
                )
                docs.append(doc)
                
            return ProjectContextDTO(
                project_name=project_name,
                root_page_id=project_page_id,
                documents=docs
            )

        except Exception as e:
            logger.error(f"Error resolving project context for {project_name}: {e}")
            raise ProviderError(
                provider=ResearchProviderType.CONFLUENCE,
                message=f"Failed to resolve project context: {e}",
                retryable=True
            )
