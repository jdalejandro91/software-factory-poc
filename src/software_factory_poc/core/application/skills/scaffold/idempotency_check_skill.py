import logging
from dataclasses import dataclass

from software_factory_poc.core.application.ports import TrackerPort, VcsPort
from software_factory_poc.core.application.skills.skill import BaseSkill

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IdempotencyCheckInput:
    """Input contract for the idempotency check."""

    mission_key: str
    branch_name: str


class IdempotencyCheckSkill(BaseSkill[IdempotencyCheckInput, bool]):
    """Reports start to Jira, then checks whether a branch already exists.

    Returns ``True`` when the branch exists (caller should abort the flow).
    """

    def __init__(self, vcs: VcsPort, tracker: TrackerPort) -> None:
        self._vcs = vcs
        self._tracker = tracker

    async def execute(self, input_data: IdempotencyCheckInput) -> bool:
        await self._tracker.add_comment(
            input_data.mission_key,
            "Iniciando tarea de Scaffolding (BrahMAS Engine)...",
        )

        branch_exists = await self._vcs.validate_branch_existence(input_data.branch_name)

        if branch_exists:
            msg = (
                f"La rama '{input_data.branch_name}' ya existe en el repositorio. "
                "Deteniendo ejecucion para evitar sobreescritura."
            )
            logger.warning("[IdempotencyCheck] %s", msg)
            await self._tracker.add_comment(input_data.mission_key, msg)
            await self._tracker.update_status(input_data.mission_key, "In Review")
            return True

        return False
