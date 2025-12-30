from software_factory_poc.application.core.ports.knowledge_base_port import KnowledgeBasePort
from software_factory_poc.infrastructure.providers.knowledge.architecture_constants import (
    SHOPPING_CART_ARCHITECTURE,
    DEFAULT_ARCHITECTURE,
)
from software_factory_poc.infrastructure.observability.logger_factory_service import build_logger

logger = build_logger(__name__)

class ConfluenceMockAdapter(KnowledgeBasePort):
    def get_knowledge(self, url: str) -> str:
        logger.info(f"Fetching knowledge from Confluence: {url}")
        
        if "carrito-de-compra" in url:
            logger.info("Match found: Shopping Cart Architecture")
            return SHOPPING_CART_ARCHITECTURE
            
        logger.info("No specific match found, returning default guidelines")
        return DEFAULT_ARCHITECTURE
