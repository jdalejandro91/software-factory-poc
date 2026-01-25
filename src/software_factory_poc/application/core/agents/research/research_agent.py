from dataclasses import dataclass
from typing import Dict
import logging

from software_factory_poc.application.core.agents.base_agent import BaseAgent
from software_factory_poc.application.core.agents.research.ports.research_gateway import ResearchGateway
from software_factory_poc.application.core.agents.scaffolding.config.scaffolding_agent_config import ScaffoldingAgentConfig

logger = logging.getLogger(__name__)

@dataclass
class ResearchAgent(BaseAgent):
    """
    Agent responsible for researching architectural standards and context.
    """
    gateway: ResearchGateway
    config: ScaffoldingAgentConfig

    def investigate(self, query: str) -> str:
        # Check if query implies architecture and we have a configured page ID
        if self._is_architecture_query(query) and self.config.architecture_page_id:
            logger.info(f"Architecture query detected. Fetching page ID: {self.config.architecture_page_id}")
            context = self.gateway.get_page_content(self.config.architecture_page_id)
        else:
            logger.info(f"General research query: {query}")
            context = self.gateway.retrieve_context(query)
        
        if not context or len(context) < 100:
             logger.warning(f"Context retrieval yielded empty or short result for query: {query}")
             if not context:
                 return "No context found."
             
        return context

    def _is_architecture_query(self, query: str) -> bool:
        terms = ["architecture", "arquitectura", "standard", "estándar", "guideline", "lineamiento"]
        q = query.lower()
        return any(term in q for term in terms)
