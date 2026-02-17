"""Unit tests — FetchReviewDiffSkill (zero I/O, AsyncMock for Ports)."""

from unittest.mock import AsyncMock

from software_factory_poc.core.application.skills.review.fetch_review_diff_skill import (
    FetchReviewDiffInput,
    FetchReviewDiffSkill,
)


class TestFetchReviewDiffSkill:
    async def test_fetches_diff_and_conventions(self) -> None:
        vcs = AsyncMock()
        docs = AsyncMock()
        vcs.get_merge_request_diff.return_value = "diff --git a/f.py"
        docs.get_architecture_context.return_value = "style conventions"
        skill = FetchReviewDiffSkill(vcs=vcs, docs=docs)

        result = await skill.execute(FetchReviewDiffInput(mr_iid="42", context_query="auth module"))

        assert result.mr_diff == "diff --git a/f.py"
        assert result.conventions == "style conventions"
        vcs.get_merge_request_diff.assert_awaited_once_with("42")
        docs.get_architecture_context.assert_awaited_once_with("auth module")
