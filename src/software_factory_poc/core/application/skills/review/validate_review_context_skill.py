import logging
import re
from dataclasses import dataclass

from software_factory_poc.core.application.ports.tracker_port import TrackerPort
from software_factory_poc.core.application.skills.skill import BaseSkill
from software_factory_poc.core.domain.mission.entities.mission import Mission

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ReviewContext:
    """Validated output of the review context extraction."""

    mr_url: str
    gitlab_project_id: str
    mr_iid: str


class ValidateReviewContextSkill(BaseSkill[Mission, ReviewContext]):
    """Extracts and validates code_review_params from the mission, reports start to Jira.

    Raises ``ValueError`` if required metadata is missing or the MR IID cannot be parsed.
    """

    def __init__(self, tracker: TrackerPort) -> None:
        self._tracker = tracker

    async def execute(self, input_data: Mission) -> ReviewContext:
        await self._tracker.add_comment(
            input_data.key,
            "Iniciando analisis de codigo (BrahMAS Code Review)...",
        )

        cr_params = input_data.description.config.get("code_review_params", {})
        mr_url = cr_params.get("review_request_url", "")
        gitlab_project_id = cr_params.get("gitlab_project_id", "")

        if not mr_url:
            raise ValueError(
                "No se encontro 'review_request_url' en la metadata de la tarea. "
                "El Scaffolder debe inyectar estos datos antes del Code Review."
            )
        if not gitlab_project_id:
            raise ValueError("No se encontro 'gitlab_project_id' en la metadata de la tarea.")

        mr_iid = self._extract_mr_iid(mr_url)

        logger.info("[ValidateReviewContext] MR IID: %s | Project: %s", mr_iid, gitlab_project_id)
        return ReviewContext(mr_url=mr_url, gitlab_project_id=gitlab_project_id, mr_iid=mr_iid)

    @staticmethod
    def _extract_mr_iid(mr_url: str) -> str:
        """Extract the MR IID from a GitLab Merge Request URL."""
        match = re.search(r"merge_requests/(\d+)", mr_url)
        if match:
            return match.group(1)
        if mr_url.strip().isdigit():
            return mr_url.strip()
        raise ValueError(f"No se pudo extraer MR IID de la URL: '{mr_url}'")
