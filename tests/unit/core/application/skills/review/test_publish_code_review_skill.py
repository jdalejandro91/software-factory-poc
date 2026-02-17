"""Unit tests — PublishCodeReviewSkill (zero I/O, AsyncMock for Ports)."""

from unittest.mock import AsyncMock

from software_factory_poc.core.application.skills.review.publish_code_review_skill import (
    PublishCodeReviewInput,
    PublishCodeReviewSkill,
)
from software_factory_poc.core.domain.quality.code_review_report import CodeReviewReport
from software_factory_poc.core.domain.quality.value_objects.review_comment import ReviewComment
from software_factory_poc.core.domain.quality.value_objects.review_severity import ReviewSeverity


def _make_input(approved: bool = True) -> PublishCodeReviewInput:
    comments = []
    if not approved:
        comments.append(
            ReviewComment(
                file_path="src/bad.py",
                description="Issue found",
                suggestion="Fix it",
                severity=ReviewSeverity.WARNING,
                line_number=10,
            )
        )
    return PublishCodeReviewInput(
        mission_key="PROJ-30",
        mr_iid="88",
        mr_url="https://gitlab.com/mr/88",
        report=CodeReviewReport(
            is_approved=approved,
            summary="Review summary",
            comments=comments,
        ),
    )


class TestPublishCodeReviewSkill:
    async def test_approved_publishes_and_comments_success(self) -> None:
        vcs = AsyncMock()
        tracker = AsyncMock()
        skill = PublishCodeReviewSkill(vcs=vcs, tracker=tracker)

        await skill.execute(_make_input(approved=True))

        vcs.publish_review.assert_awaited_once_with("88", _make_input(approved=True).report)
        tracker.post_review_summary.assert_awaited_once()
        # Should post an APROBADO comment
        comment_call = tracker.add_comment.call_args
        assert "APROBADO" in comment_call[0][1]

    async def test_rejected_transitions_to_changes_requested(self) -> None:
        vcs = AsyncMock()
        tracker = AsyncMock()
        skill = PublishCodeReviewSkill(vcs=vcs, tracker=tracker)

        await skill.execute(_make_input(approved=False))

        # Should post a RECHAZADO comment and update status
        comment_call = tracker.add_comment.call_args
        assert "RECHAZADO" in comment_call[0][1]
        tracker.update_status.assert_awaited_once_with("PROJ-30", "Changes Requested")

    async def test_approved_does_not_transition_status(self) -> None:
        vcs = AsyncMock()
        tracker = AsyncMock()
        skill = PublishCodeReviewSkill(vcs=vcs, tracker=tracker)

        await skill.execute(_make_input(approved=True))

        tracker.update_status.assert_not_awaited()
