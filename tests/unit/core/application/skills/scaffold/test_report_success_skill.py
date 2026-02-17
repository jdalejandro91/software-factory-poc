"""Unit tests — ReportSuccessSkill (zero I/O, AsyncMock for Ports)."""

from unittest.mock import AsyncMock

from software_factory_poc.core.application.skills.scaffold.report_success_skill import (
    ReportSuccessInput,
    ReportSuccessSkill,
)


def _make_input() -> ReportSuccessInput:
    return ReportSuccessInput(
        mission_key="PROJ-50",
        gitlab_project_id="42",
        branch_name="feature/proj-50",
        mr_url="https://gitlab.com/mr/5",
        commit_hash="abc123",
        files_count=3,
    )


class TestReportSuccessSkill:
    async def test_posts_metadata_and_success_comments(self) -> None:
        tracker = AsyncMock()
        skill = ReportSuccessSkill(tracker=tracker)

        await skill.execute(_make_input())

        assert tracker.add_comment.await_count == 2

    async def test_transitions_status_to_in_review(self) -> None:
        tracker = AsyncMock()
        skill = ReportSuccessSkill(tracker=tracker)

        await skill.execute(_make_input())

        tracker.update_status.assert_awaited_once_with("PROJ-50", "In Review")

    async def test_metadata_comment_contains_yaml_block(self) -> None:
        tracker = AsyncMock()
        skill = ReportSuccessSkill(tracker=tracker)

        await skill.execute(_make_input())

        metadata_call = tracker.add_comment.call_args_list[0]
        comment_text = metadata_call[0][1]
        assert "```yaml" in comment_text
        assert "gitlab_project_id" in comment_text
        assert "42" in comment_text

    async def test_success_comment_contains_mr_url(self) -> None:
        tracker = AsyncMock()
        skill = ReportSuccessSkill(tracker=tracker)

        await skill.execute(_make_input())

        success_call = tracker.add_comment.call_args_list[1]
        comment_text = success_call[0][1]
        assert "https://gitlab.com/mr/5" in comment_text
        assert "3" in comment_text
