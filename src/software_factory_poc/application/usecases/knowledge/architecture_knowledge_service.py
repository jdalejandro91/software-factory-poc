from __future__ import annotations

import time
from typing import Optional

from software_factory_poc.application.ports.drivers.research.ports.confluence_provider import ConfluenceProvider
from software_factory_poc.infrastructure.configuration.tool_settings import ToolSettings


class ArchitectureKnowledgeService:
    def __init__(self, provider: ConfluenceProvider, settings: ToolSettings) -> None:
        self.client = provider
        self.page_id = settings.architecture_doc_page_id
        
        # Simple in-memory cache
        self._cache:Optional[ str] = None
        self._cache_timestamp: float = 0.0
        self._cache_ttl_seconds: float = 300.0  # 5 minutes default

    def get_architecture_guidelines(self) -> str:
        """
        Retrieves the architecture guidelines from Confluence, using a cache.
        """
        now = time.time()
        if self._cache and (now - self._cache_timestamp < self._cache_ttl_seconds):
            return self._cache
        
        content = self.client.get_page_content(self.page_id)
        
        # Update cache
        self._cache = content
        self._cache_timestamp = now
        
        return content
