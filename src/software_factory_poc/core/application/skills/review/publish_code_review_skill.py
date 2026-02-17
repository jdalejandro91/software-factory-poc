import logging
from dataclasses import dataclass

from software_factory_poc.core.application.ports import TrackerPort, VcsPort
from software_factory_poc.core.application.skills.skill import BaseSkill
from software_factory_poc.core.domain.quality import CodeReviewReport

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PublishCodeReviewInput:
    """Input contract for the review publish step."""

    mission_key: str
    mr_iid: str
    mr_url: str
    report: CodeReviewReport


class PublishCodeReviewSkill(BaseSkill[PublishCodeReviewInput, None]):
    """Publishes the review to GitLab, posts summary to Jira, and transitions the ticket."""

    def __init__(self, vcs: VcsPort, tracker: TrackerPort) -> None:
        self._vcs = vcs
        self._tracker = tracker

    async def execute(self, input_data: PublishCodeReviewInput) -> None:
        logger.info("[PublishCodeReview] Publishing comments to GitLab MR %s", input_data.mr_iid)
        await self._vcs.publish_review(input_data.mr_iid, input_data.report)

        logger.info("[PublishCodeReview] Posting summary to Jira %s", input_data.mission_key)
        await self._tracker.post_review_summary(input_data.mission_key, input_data.report)

        if input_data.report.is_approved:
            await self._tracker.add_comment(
                input_data.mission_key,
                f"Code Review APROBADO. El MR cumple los estandares de calidad.\n"
                f"MR: {input_data.mr_url}",
            )
        else:
            await self._tracker.add_comment(
                input_data.mission_key,
                f"Code Review RECHAZADO. Se requieren cambios antes de aprobar.\n"
                f"Issues encontrados: {len(input_data.report.comments)}\n"
                f"MR: {input_data.mr_url}",
            )
            await self._tracker.update_status(input_data.mission_key, "Changes Requested")

        verdict = "APPROVED" if input_data.report.is_approved else "REJECTED"
        logger.info(
            "[PublishCodeReview] %s reviewed — Verdict: %s", input_data.mission_key, verdict
        )
