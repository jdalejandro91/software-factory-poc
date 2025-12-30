from software_factory_poc.application.core.ports.gateways.knowledge_gateway import KnowledgeGateway
from software_factory_poc.infrastructure.observability.logger_factory_service import (
    LoggerFactoryService,
)
from software_factory_poc.infrastructure.providers.knowledge.architecture_constants import (
    DEFAULT_ARCHITECTURE,
    SHOPPING_CART_ARCHITECTURE,
)

logger = LoggerFactoryService.build_logger(__name__)

class ConfluenceMockAdapter(KnowledgeGateway):
    def retrieve_context(self, query: str) -> str:
        logger.info(f"Fetching context for query: {query}")
        
        query_lower = query.lower()
        if "shopping cart" in query_lower or "carrito" in query_lower:
            logger.info("Match found: Shopping Cart Architecture")
            return SHOPPING_CART_ARCHITECTURE
            
        logger.info("No specific match found, returning default guidelines")
        return DEFAULT_ARCHITECTURE

    # Legacy support if needed during transition (though mostly dead)
    def get_knowledge(self, url: str) -> str:
        return self.retrieve_context(url)
