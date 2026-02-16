import os
import re
from typing import Any
from html.parser import HTMLParser

from software_factory_poc.application.drivers.common import ProviderError
from software_factory_poc.application.drivers import ResearchProviderType
from software_factory_poc.application.drivers.research.ports.research_gateway import ResearchGateway
from software_factory_poc.infrastructure.configuration.tools.confluence.confluence_settings import ConfluenceSettings
from software_factory_poc.infrastructure.observability.logger_factory_service import LoggerFactoryService
from software_factory_poc.infrastructure.drivers.research.clients.confluence_http_client import ConfluenceHttpClient
from software_factory_poc.application.drivers import DocumentContentDTO
from software_factory_poc.application.drivers import ProjectContextDTO

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

    def _traverse_path(self, segments: list[str]) -> str | None:
        """
        Traverses a hierarchical path in Confluence segment by segment.
        Returns the ID of the final node if found, else None.
        Query logic:
        - Root: space="{key}" AND title="{segment}"
        - Child: parent={id} AND title="{segment}"
        Note: We omit 'type="page"' to support "folders" or other content types acting as containers.
        """
        current_parent_id = None
        
        path_str = " / ".join(segments)
        logger.debug(f"Starting Path Traversal: {path_str}")

        for i, segment in enumerate(segments):
            if current_parent_id is None:
                # Root Search
                cql = f'space = "{self.space_key}" AND title = "{segment}"'
            else:
                # Child Search
                cql = f'parent = {current_parent_id} AND title = "{segment}"'
                
            try:
                # We use strict search first.
                results = self.http_client.search(cql)
                
                if not results:
                     # Attempt case-insensitive match/normalization search if strict fails?
                     # For now, strict title match as per requirements for "Explicit Path"
                     logger.debug(f"Path traversal broken at segment '{segment}'.")
                     return None
                
                # Assume first match is correct (titles should be unique under a parent)
                node = results[0]
                current_parent_id = node['id']
                # logger.debug(f"   + Resolved '{segment}' -> ID: {current_parent_id}")
                
            except Exception as e:
                logger.warning(f"Error traversing path at segment '{segment}': {e}")
                return None
                
        return current_parent_id

    def get_project_context(self, project_name: str) -> ProjectContextDTO:
        """
        Retrieves project-specific documentation from Confluence.
        Algorithm:
        1. Explicit Path Traversal (Full & Short)
        2. Direct Search (Fuzzy)
        3. Bag of Words Search
        4. List & Filter
        """
        try:
            logger.info(f"Retrieving Project Context for: '{project_name}' (Space: {self.space_key})")
            
            project_folder_id = None
            
            # Strategies defined in order of precision/safety
            
            # Strategy 1: Full Explicit Path
            # Path: Desarrollo de software / projects / {project_name}
            if not project_folder_id:
                full_path = ["Desarrollo de software", "projects", project_name]
                project_folder_id = self._traverse_path(full_path)
                if project_folder_id:
                    logger.info(f"📍 Context found via Full Path Traversal: /{' / '.join(full_path)} (ID: {project_folder_id})")

            # Strategy 2: Short Explicit Path
            # Path: projects / {project_name}
            if not project_folder_id:
                short_path = ["projects", project_name]
                project_folder_id = self._traverse_path(short_path)
                if project_folder_id:
                    logger.info(f"📍 Context found via Short Path Traversal: /{' / '.join(short_path)} (ID: {project_folder_id})")

            # Strategy 3: Legacy Hierarchical (Root "projects" (fuzzy) -> Child)
            # This is essentially covered by Strategy 2 but uses 'IN ("projects", "Projects")' logic
            if not project_folder_id:
                try:
                    root_cql = f'space = "{self.space_key}" AND title in ("projects", "Projects")'
                    root_results = self.http_client.search(root_cql)
                    
                    if root_results:
                        root_id = root_results[0]["id"]
                        project_cql = f'parent = {root_id} AND title = "{project_name}"'
                        project_results = self.http_client.search(project_cql)
                        
                        if project_results:
                            project_folder_id = project_results[0]["id"]
                            logger.info(f"📂 Found Project Folder '{project_name}' via Legacy Root Search (ID: {project_folder_id})")
                except Exception as e:
                    logger.warning(f"Legacy Hierarchical search failed: {e}")

            # Strategy 4: Direct Search (Fuzzy)
            if not project_folder_id:
                logger.info("⚠️ Hierarchical strategies failed. Attempting Direct Search strategy (Fuzzy)...")
                logger.info(f"Trying Fuzzy Search for '{project_name}'...")
                
                # Use CONTAINS operator (~) to handle hyphens tokenization
                direct_cql = f'space = "{self.space_key}" AND title ~ "{project_name}"'
                direct_results = self.http_client.search(direct_cql)
                
                if direct_results:
                    # Filter: Find the best match where normalized title equals project_name
                    normalized_target = project_name.lower().strip()
                    for res in direct_results:
                        res_title = res.get("title", "").lower().replace(" ", "-") # normalize Confluence title to kebab-case
                        if res_title == normalized_target:
                            project_folder_id = res["id"]
                            logger.info(f"🎯 Found project folder directly: {project_name} (ID: {project_folder_id}). Fetching children...")
                            break
                    
                    if not project_folder_id:
                        logger.warning(f"Fuzzy search returned {len(direct_results)} results but no exact title match for '{project_name}'.")

            # Strategy 5: Bag of Words Search (Hyphen-Agnostic)
            if not project_folder_id:
                parts = re.split(r'[-_ ]+', project_name)
                parts = [p.strip().lower() for p in parts if p.strip()]  # Remove empty strings & lowercase for CQL safety
                
                if len(parts) > 1:
                    logger.info(f"⚠️ Direct Fuzzy search failed. Attempting Bag of Words strategy for parts: {parts}...")
                    
                    # Construct OR query for all parts to be resilient against tokenization issues
                    # title ~ "part1" OR title ~ "part2"
                    or_clauses = [f'title ~ "{part}"' for part in parts]
                    bag_cql = f'space = "{self.space_key}" AND ({" OR ".join(or_clauses)})'
                    
                    bag_results = self.http_client.search(bag_cql, limit=50)
                    
                    if bag_results:
                        # Filter: "shopping cart" in "project shopping cart".normalized()
                        # Normalization: lower, replace -/_ with SPACE
                        target_norm = project_name.lower().replace("-", " ").replace("_", " ").strip()
                        
                        for res in bag_results:
                            found_title_norm = res.get("title", "").lower().replace("-", " ").replace("_", " ").strip()
                            
                            if target_norm in found_title_norm:
                                project_folder_id = res["id"]
                                logger.info(f"✅ Found folder '{res.get('title')}' (ID: {project_folder_id}) using Tokenized Search.")
                                break
                        
                        if not project_folder_id:
                             logger.warning(f"Bag of Words returned {len(bag_results)} candidates but none matched normalized target '{target_norm}'.")

            # Strategy 6: List & Filter Recent Pages (Last Resort)
            if not project_folder_id:
                logger.info("⚠️ Bag of Words failed. Attempting 'List & Filter' strategy usage recent pages...")
                # Fetch recent pages (e.g., last 50-100 modified/created)
                # Note: 'recentlyUpdated' might be better than created if it's active.
                list_cql = f'space = "{self.space_key}" order by lastModified desc'
                # We assume http_client.search uses a default limit (often 10-25). 
                # Ideally we want more assurance, but let's trust "limit=50" if search supports it or default is sufficient.
                # Since search takes just cql string in current interface, we rely on default or string limit if supported.
                # Confluence CQL supports 'limit X' but provider might wrap it. 
                # We use the explicit limit parameter of the client.
                
                recent_results = self.http_client.search(list_cql, limit=50)
                
                if recent_results:
                     target_norm = project_name.lower().replace(" ", "").replace("-", "").replace("_", "")
                     for res in recent_results:
                        found_title_norm = res.get("title", "").lower().replace(" ", "").replace("-", "").replace("_", "")
                        
                        # Exact normalized match check specifically here to be safer than "in" for this broad list
                        # Or 'in' if we want to catch "Project: Shopping Cart"
                        if target_norm in found_title_norm:
                            project_folder_id = res["id"]
                            logger.info(f"🎯 Found project folder via List & Filter: {res.get('title')} (ID: {project_folder_id}). Fetching children...")
                            break
                            
            # Validate Result
            if not project_folder_id:
                raise ProviderError(
                    provider=ResearchProviderType.CONFLUENCE,
                    message=f"Project folder '{project_name}' NOT FOUND (searched hierarchically & directly in space {self.space_key})",
                    retryable=False
                )
            
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
            for doc in docs:
                logger.debug(f"   - Found Doc: {doc.title} (ID: {doc.metadata.get('id')})")
            
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
