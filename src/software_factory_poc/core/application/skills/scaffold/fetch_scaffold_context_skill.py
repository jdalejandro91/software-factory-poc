import logging

from software_factory_poc.core.application.ports.docs_port import DocsPort
from software_factory_poc.core.application.skills.skill import BaseSkill

logger = logging.getLogger(__name__)


class FetchScaffoldContextSkill(BaseSkill[str, str]):
    """Fetches architecture context from the documentation provider.

    Input is the service name (or mission key as fallback).
    Returns the raw architecture context string.
    """

    def __init__(self, docs: DocsPort) -> None:
        self._docs = docs

    async def execute(self, input_data: str) -> str:
        logger.info("[FetchScaffoldContext] Fetching architecture context for '%s'", input_data)
        return await self._docs.get_architecture_context(input_data)
