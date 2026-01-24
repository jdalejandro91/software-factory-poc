from dataclasses import dataclass
import logging

from software_factory_poc.application.core.domain.agents.base_agent import BaseAgent
from software_factory_poc.application.core.ports.gateways.knowledge_gateway import KnowledgeGateway

logger = logging.getLogger(__name__)

@dataclass
class KnowledgeAgent(BaseAgent):
    """
    Agent responsible for retrieving similar existing solutions or historical data.
    """
    gateway: KnowledgeGateway

    def retrieve_similar_solutions(self, topic: str) -> str:
        logger.info("Knowledge retrieval skipped (not configured yet).")
        return ""
