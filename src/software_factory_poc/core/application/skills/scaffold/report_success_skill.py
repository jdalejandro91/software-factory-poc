import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from software_factory_poc.core.application.ports import TrackerPort
from software_factory_poc.core.application.skills.skill import BaseSkill

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ReportSuccessInput:
    """Input contract for the final success report."""

    mission_key: str
    gitlab_project_id: str
    branch_name: str
    mr_url: str
    commit_hash: str
    files_count: int


class ReportSuccessSkill(BaseSkill[ReportSuccessInput, None]):
    """Posts metadata + success comment to Jira and transitions the ticket to In Review."""

    def __init__(self, tracker: TrackerPort) -> None:
        self._tracker = tracker

    async def execute(self, input_data: ReportSuccessInput) -> None:
        metadata_comment = self._build_metadata_comment(
            gitlab_project_id=input_data.gitlab_project_id,
            branch_name=input_data.branch_name,
            mr_url=input_data.mr_url,
        )
        await self._tracker.add_comment(input_data.mission_key, metadata_comment)

        success_msg = (
            f"Scaffolding completado exitosamente.\n"
            f"- Merge Request: {input_data.mr_url}\n"
            f"- Rama: {input_data.branch_name}\n"
            f"- Commit: {input_data.commit_hash}\n"
            f"- Archivos generados: {input_data.files_count}"
        )
        await self._tracker.add_comment(input_data.mission_key, success_msg)

        await self._tracker.update_status(input_data.mission_key, "In Review")

        logger.info(
            "[ReportSuccess] Reported success for %s — MR: %s",
            input_data.mission_key,
            input_data.mr_url,
        )

    @staticmethod
    def _build_metadata_comment(gitlab_project_id: str, branch_name: str, mr_url: str) -> str:
        """Build the YAML metadata block for the Jira comment."""
        generated_at = datetime.now(UTC).isoformat()
        return (
            "BrahMAS Automation Metadata:\n"
            "```yaml\n"
            "code_review_params:\n"
            f'  gitlab_project_id: "{gitlab_project_id}"\n'
            f'  source_branch_name: "{branch_name}"\n'
            f'  review_request_url: "{mr_url}"\n'
            f'  generated_at: "{generated_at}"\n'
            "```"
        )
