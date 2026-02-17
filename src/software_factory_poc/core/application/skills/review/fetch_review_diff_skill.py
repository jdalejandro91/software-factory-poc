import logging
from dataclasses import dataclass

from software_factory_poc.core.application.ports.docs_port import DocsPort
from software_factory_poc.core.application.ports.vcs_port import VcsPort
from software_factory_poc.core.application.skills.skill import BaseSkill

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FetchReviewDiffInput:
    """Input contract for fetching review diff and architecture context."""

    mr_iid: str
    context_query: str


@dataclass(frozen=True)
class FetchReviewDiffOutput:
    """Output carrying the MR diff and architecture conventions."""

    mr_diff: str
    conventions: str


class FetchReviewDiffSkill(BaseSkill[FetchReviewDiffInput, FetchReviewDiffOutput]):
    """Fetches the MR diff from VCS and architecture context from Docs."""

    def __init__(self, vcs: VcsPort, docs: DocsPort) -> None:
        self._vcs = vcs
        self._docs = docs

    async def execute(self, input_data: FetchReviewDiffInput) -> FetchReviewDiffOutput:
        logger.info("[FetchReviewDiff] Downloading diff for MR %s", input_data.mr_iid)
        mr_diff = await self._vcs.get_merge_request_diff(input_data.mr_iid)

        logger.info(
            "[FetchReviewDiff] Fetching architecture context for '%s'", input_data.context_query
        )
        conventions = await self._docs.get_architecture_context(input_data.context_query)

        return FetchReviewDiffOutput(mr_diff=mr_diff, conventions=conventions)
