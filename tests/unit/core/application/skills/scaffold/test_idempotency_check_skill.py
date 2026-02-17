"""Unit tests — IdempotencyCheckSkill (zero I/O, AsyncMock for Ports)."""

from unittest.mock import AsyncMock

from software_factory_poc.core.application.skills.scaffold.idempotency_check_skill import (
    IdempotencyCheckInput,
    IdempotencyCheckSkill,
)


def _build_skill() -> tuple[IdempotencyCheckSkill, AsyncMock, AsyncMock]:
    vcs = AsyncMock()
    tracker = AsyncMock()
    return IdempotencyCheckSkill(vcs=vcs, tracker=tracker), vcs, tracker


class TestIdempotencyCheckSkill:
    async def test_returns_false_when_branch_does_not_exist(self) -> None:
        skill, vcs, tracker = _build_skill()
        vcs.validate_branch_existence.return_value = False

        result = await skill.execute(
            IdempotencyCheckInput(mission_key="PROJ-1", branch_name="feature/proj-1")
        )

        assert result is False
        tracker.add_comment.assert_awaited_once()
        vcs.validate_branch_existence.assert_awaited_once_with("feature/proj-1")

    async def test_returns_true_when_branch_exists_and_reports(self) -> None:
        skill, vcs, tracker = _build_skill()
        vcs.validate_branch_existence.return_value = True

        result = await skill.execute(
            IdempotencyCheckInput(mission_key="PROJ-2", branch_name="feature/proj-2")
        )

        assert result is True
        # Should have called add_comment twice: start + abort notice
        assert tracker.add_comment.await_count == 2
        tracker.update_status.assert_awaited_once_with("PROJ-2", "In Review")

    async def test_always_reports_start_to_tracker(self) -> None:
        skill, vcs, tracker = _build_skill()
        vcs.validate_branch_existence.return_value = False

        await skill.execute(
            IdempotencyCheckInput(mission_key="PROJ-3", branch_name="feature/proj-3")
        )

        first_call = tracker.add_comment.call_args_list[0]
        assert first_call[0][0] == "PROJ-3"
        assert "Iniciando" in first_call[0][1]
