"""Unit tests — ValidateReviewContextSkill (zero I/O, AsyncMock for Ports)."""

from unittest.mock import AsyncMock

import pytest

from software_factory_poc.core.application.skills.review.validate_review_context_skill import (
    ValidateReviewContextSkill,
)
from software_factory_poc.core.domain.mission import Mission, TaskDescription


def _make_mission(
    mr_url: str = "https://gitlab.example.com/merge_requests/77",
    project_id: str = "42",
) -> Mission:
    return Mission(
        id="1",
        key="PROJ-10",
        summary="Review MR",
        status="In Progress",
        project_key="PROJ",
        issue_type="Code Review",
        description=TaskDescription(
            raw_content="Review the MR",
            config={
                "code_review_params": {
                    "review_request_url": mr_url,
                    "gitlab_project_id": project_id,
                },
            },
        ),
    )


class TestValidateReviewContextSkill:
    async def test_extracts_review_context_from_mission(self) -> None:
        tracker = AsyncMock()
        skill = ValidateReviewContextSkill(tracker=tracker)

        result = await skill.execute(_make_mission())

        assert result.mr_url == "https://gitlab.example.com/merge_requests/77"
        assert result.gitlab_project_id == "42"
        assert result.mr_iid == "77"

    async def test_reports_start_to_tracker(self) -> None:
        tracker = AsyncMock()
        skill = ValidateReviewContextSkill(tracker=tracker)

        await skill.execute(_make_mission())

        tracker.add_comment.assert_awaited_once()
        assert "Iniciando" in tracker.add_comment.call_args[0][1]

    async def test_raises_when_mr_url_missing(self) -> None:
        tracker = AsyncMock()
        skill = ValidateReviewContextSkill(tracker=tracker)
        mission = _make_mission(mr_url="")

        with pytest.raises(ValueError, match="review_request_url"):
            await skill.execute(mission)

    async def test_raises_when_project_id_missing(self) -> None:
        tracker = AsyncMock()
        skill = ValidateReviewContextSkill(tracker=tracker)
        mission = _make_mission(project_id="")

        with pytest.raises(ValueError, match="gitlab_project_id"):
            await skill.execute(mission)

    async def test_raises_when_mr_iid_cannot_be_parsed(self) -> None:
        tracker = AsyncMock()
        skill = ValidateReviewContextSkill(tracker=tracker)
        mission = _make_mission(mr_url="https://gitlab.example.com/not-a-valid-url")

        with pytest.raises(ValueError, match="No se pudo extraer"):
            await skill.execute(mission)


class TestExtractMrIid:
    def test_extracts_from_standard_url(self) -> None:
        iid = ValidateReviewContextSkill._extract_mr_iid(
            "https://gitlab.example.com/group/project/-/merge_requests/123"
        )
        assert iid == "123"

    def test_extracts_from_plain_number(self) -> None:
        iid = ValidateReviewContextSkill._extract_mr_iid("456")
        assert iid == "456"

    def test_raises_for_invalid_url(self) -> None:
        with pytest.raises(ValueError):
            ValidateReviewContextSkill._extract_mr_iid("not-a-url")
