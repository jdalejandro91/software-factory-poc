import time

from software_factory_poc.application.core.ports.knowledge_base_port import KnowledgeBasePort
from software_factory_poc.application.core.ports.tools.confluence_provider import ConfluenceProvider
from software_factory_poc.infrastructure.configuration.tool_settings import ToolSettings
from software_factory_poc.infrastructure.observability.logger_factory_service import (
    LoggerFactoryService,
)

logger = LoggerFactoryService.build_logger(__name__)

class ConfluenceServiceAdapter(KnowledgeBasePort):
    def __init__(self, provider: ConfluenceProvider, settings: ToolSettings):
        self.provider = provider
        self.page_id = settings.architecture_doc_page_id
        self._cache = None
        self._cache_time = 0
        self._ttl = 300  # 5 minutos

    def get_knowledge(self, url: str) -> str:
        # Verificar caché
        if self._cache and (time.time() - self._cache_time < self._ttl):
            logger.info("Returning cached Confluence knowledge.")
            return self._cache

        logger.info(f"Fetching real knowledge from Confluence Page ID: {self.page_id}")
        content = self.provider.get_page_content(self.page_id)
        
        # Actualizar caché
        self._cache = content
        self._cache_time = time.time()
        return content
