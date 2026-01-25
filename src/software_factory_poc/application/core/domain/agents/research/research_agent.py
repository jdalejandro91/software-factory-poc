from dataclasses import dataclass
from typing import Dict
import logging

from software_factory_poc.application.core.domain.agents.base_agent import BaseAgent
from software_factory_poc.application.core.domain.agents.research.ports.research_gateway import ResearchGateway

logger = logging.getLogger(__name__)

@dataclass
class ResearchAgent(BaseAgent):
    """
    Agent responsible for researching architectural standards and context.
    """
    gateway: ResearchGateway

    def investigate(self, query: str) -> str:
        # User requested direct query passing, relying on Gateway/Config for specifics
        context = self.gateway.retrieve_context(query)
        
        if not context or len(context) < 100:
             logger.warning(f"Context retrieval yielded empty or short result for query: {query}")
             
        return context
