from dataclasses import dataclass
from typing import Dict
import logging

from software_factory_poc.application.core.domain.agents.base_agent import BaseAgent
from software_factory_poc.application.core.ports.gateways.knowledge_gateway import KnowledgeGateway

logger = logging.getLogger(__name__)

@dataclass
class ResearchAgent(BaseAgent):
    """
    Agent responsible for researching architectural standards and context.
    """
    gateway: KnowledgeGateway

    def investigate(self, query: str, filters: Dict) -> str:
        # Merge query into filters/criteria
        search_criteria = {**filters, "query": query}
        context = self.gateway.retrieve_context(search_criteria)
        
        if not context or len(context) < 100:
             logger.warning(f"Context retrieval yielded empty or short result for query: {query}")
             
        return context
