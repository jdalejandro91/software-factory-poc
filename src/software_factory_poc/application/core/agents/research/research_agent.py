import logging
from dataclasses import dataclass
from typing import Optional

from software_factory_poc.application.core.agents.base_agent import BaseAgent
from software_factory_poc.application.core.agents.research.ports.research_gateway import ResearchGateway
from software_factory_poc.application.core.agents.scaffolding.config.scaffolding_agent_config import \
    ScaffoldingAgentConfig

logger = logging.getLogger(__name__)


@dataclass
class ResearchAgent(BaseAgent):
    """
    Agent responsible for researching architectural standards and context.
    """
    gateway: ResearchGateway
    config: ScaffoldingAgentConfig

    def investigate(self, query: str, specific_page_id: Optional[str] = None) -> str:
        # Priority 1: Specific Page ID
        if specific_page_id:
            logger.info(f"🔍 Fetching specific documentation ID: {specific_page_id}")
            try:
                content = self.gateway.get_page_content(specific_page_id)
                logger.info(f"SPECIFIC DOC RETRIEVED ({len(content)} chars)")
                return content
            except Exception as e:
                logger.error(f"Failed to fetch specific doc {specific_page_id}: {e}")
                # Fallback to query investigation

        # Check if query implies architecture and we have a configured page ID
        if self._is_architecture_query(query) and self.config.architecture_page_id:
            logger.info(
                f"🕵️ ARCHITECTURE QUERY DETECTED. Fetching Confluence Page ID: {self.config.architecture_page_id}")
            try:
                context = self.gateway.get_page_content(self.config.architecture_page_id)
                logger.info(f"CONFLUENCE CONTENT RETRIEVED ({len(context)} chars).")
                logger.info(
                    f"⬇️ --- FULL CONFLUENCE CONTENT START --- ⬇️\n{context}\n⬆️ --- FULL CONFLUENCE CONTENT END --- ⬆️")

            except Exception as e:
                logger.error(f"Error fetching architecture page: {e}")
                context = "Error retrieving architecture. Use standard defaults."
        else:
            logger.info(f"🔎 General research query: {query}")
            context = self.gateway.retrieve_context(query)

        if not context or len(context) < 100:
            logger.warning(f"Context retrieval yielded empty or short result for query: {query}")
            if not context:
                return "No specific architecture context found. Use industry standards."

        return context

    def _is_architecture_query(self, query: str) -> bool:
        terms = ["architecture", "arquitectura", "standard", "estándar", "guideline", "lineamiento"]
        q = query.lower()
        return any(term in q for term in terms)