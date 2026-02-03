import os
import re
from typing import Any
from html.parser import HTMLParser

from software_factory_poc.application.core.agents.common.exceptions.provider_error import ProviderError
from software_factory_poc.application.core.agents.research.config.research_provider_type import ResearchProviderType
from software_factory_poc.application.core.agents.research.ports.research_gateway import ResearchGateway
from software_factory_poc.infrastructure.configuration.confluence_settings import ConfluenceSettings
from software_factory_poc.infrastructure.observability.logger_factory_service import LoggerFactoryService
from software_factory_poc.infrastructure.providers.research.clients.confluence_http_client import ConfluenceHttpClient
from software_factory_poc.application.core.agents.research.dtos.document_content_dto import DocumentContentDTO
from software_factory_poc.application.core.agents.research.dtos.project_context_dto import ProjectContextDTO

logger = LoggerFactoryService.build_logger(__name__)

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
        # 1. Configurable Space Key
        self.space_key = os.getenv("CONFLUENCE_SPACE_KEY", "DDS")

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

        # 1. Remove HTML Tags
        clean_text = re.sub(r"<[^>]+>", " ", input_text)
        
        # 2. Decode entities
        import html
        clean_text = html.unescape(clean_text)

        # 3. Collapse whitespace
        clean_text = " ".join(clean_text.split())

        return clean_text

    def get_project_context(self, project_name: str) -> ProjectContextDTO:
        """
        Retrieves project-specific documentation from Confluence.
        Algorithm:
        1. Find "projects" root page in strict Space.
        2. Find specific project folder (child of root).
        3. Fetch all children documents recursively or flatly.
        """
        try:
            logger.info(f"Retrieving Project Context for: '{project_name}' (Space: {self.space_key})")
            
            # Step A: Localizar la Página Raíz ("projects")
            root_cql = f'space = "{self.space_key}" AND type = "page" AND title in ("projects", "Projects")'
            root_results = self.http_client.search(root_cql)
            
            if not root_results:
                raise ProviderError(
                    provider=ResearchProviderType.CONFLUENCE,
                    message=f"Root folder 'projects' not found in space {self.space_key}",
                    retryable=False
                )
            
            root_id = root_results[0]["id"]
            logger.info(f"📂 Found Root 'projects' (ID: {root_id})")
            
            # Step B: Localizar la Carpeta del Proyecto
            # Strict exact match as requested
            project_cql = f'parent = {root_id} AND type = "page" AND title = "{project_name}"'
            project_results = self.http_client.search(project_cql)
            
            if not project_results:
                logger.warning(f"⚠️ Project folder '{project_name}' NOT FOUND in Confluence under parent {root_id}.")
                return ProjectContextDTO(
                    project_name=project_name,
                    root_page_id="N/A",
                    documents=[],
                )
            
            project_folder_id = project_results[0]["id"]
            logger.info(f"📂 Found Project Folder '{project_name}' (ID: {project_folder_id})")
            
            # Step C: Recuperación Masiva de Hijos (Documentos)
            all_pages = []
            start = 0
            limit = 50
            
            while True:
                # Assuming check for implicit next link or loop
                results = self.http_client.get_child_pages(
                    page_id=project_folder_id, 
                    limit=limit, 
                    expand='body.storage',
                    start=start
                )
                
                if not results:
                    break
                    
                all_pages.extend(results)
                start += len(results)
                
                # Check for pagination break
                if len(results) < limit:
                     break
            
            # Step D: Procesamiento
            docs = []
            for child in all_pages:
                # Reuse extraction logic properly
                raw_html_val = ""
                # Safely extract body.storage.value manually or reuse _extract_text
                # _extract_text Logic already finds body.storage and cleans it.
                # Let's use it to be consistent and clean.
                cleaned_content = self._extract_text(child)
                
                doc = DocumentContentDTO(
                    title=child.get("title", "Untitled"),
                    url=child.get("_links", {}).get("webui", ""),
                    content=cleaned_content,
                    metadata={
                        "id": child.get("id"),
                        "space": child.get("space", {}).get("key", "")
                    }
                )
                docs.append(doc)
                
            logger.info(f"✅ Retrieved {len(docs)} documents for project '{project_name}'")
            
            return ProjectContextDTO(
                project_name=project_name,
                root_page_id=project_folder_id,
                documents=docs
            )

        except Exception as e:
            logger.error(f"Error resolving project context for {project_name}: {e}")
            raise ProviderError(
                provider=ResearchProviderType.CONFLUENCE,
                message=f"Failed to resolve project context: {e}",
                retryable=True
            )
