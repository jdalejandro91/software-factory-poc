"""Unit tests — ApplyScaffoldDeliverySkill (zero I/O, AsyncMock for Ports)."""

from unittest.mock import AsyncMock

from software_factory_poc.core.application.agents.scaffolder.contracts.scaffolder_contracts import (
    FileSchemaDTO,
    ScaffoldingResponseSchema,
)
from software_factory_poc.core.application.skills.scaffold.apply_scaffold_delivery_skill import (
    ApplyScaffoldDeliveryInput,
    ApplyScaffoldDeliverySkill,
)


def _make_plan() -> ScaffoldingResponseSchema:
    return ScaffoldingResponseSchema(
        branch_name="feature/proj-1",
        commit_message="feat: scaffold service",
        files=[
            FileSchemaDTO(path="src/app.py", content="# app", is_new=True),
            FileSchemaDTO(path="tests/test_app.py", content="# test", is_new=True),
        ],
    )


class TestApplyScaffoldDeliverySkill:
    async def test_creates_branch_commits_and_opens_mr(self) -> None:
        vcs = AsyncMock()
        vcs.create_branch.return_value = "https://gitlab.com/tree/feature/proj-1"
        vcs.commit_changes.return_value = "abc123"
        vcs.create_merge_request.return_value = "https://gitlab.com/mr/1"
        skill = ApplyScaffoldDeliverySkill(vcs=vcs)

        mr_url = await skill.execute(
            ApplyScaffoldDeliveryInput(
                mission_key="PROJ-1",
                mission_summary="Scaffold service",
                branch_name="feature/proj-1",
                target_branch="main",
                scaffold_plan=_make_plan(),
            )
        )

        assert mr_url == "https://gitlab.com/mr/1"
        vcs.create_branch.assert_awaited_once_with("feature/proj-1", ref="main")
        vcs.commit_changes.assert_awaited_once()
        vcs.create_merge_request.assert_awaited_once()

    async def test_commit_intent_has_correct_files(self) -> None:
        vcs = AsyncMock()
        vcs.create_merge_request.return_value = "https://gitlab.com/mr/2"
        skill = ApplyScaffoldDeliverySkill(vcs=vcs)

        await skill.execute(
            ApplyScaffoldDeliveryInput(
                mission_key="PROJ-2",
                mission_summary="Scaffold",
                branch_name="feature/proj-2",
                target_branch="main",
                scaffold_plan=_make_plan(),
            )
        )

        intent = vcs.commit_changes.call_args[0][0]
        assert len(intent.files) == 2
        assert intent.files[0].path == "src/app.py"
        assert intent.branch.value == "feature/proj-2"
        assert intent.message == "feat: scaffold service"


class TestBuildBranchName:
    def test_with_service_name(self) -> None:
        result = ApplyScaffoldDeliverySkill.build_branch_name("PROJ-100", "My Service")
        assert result == "feature/proj-100-my-service"

    def test_without_service_name(self) -> None:
        result = ApplyScaffoldDeliverySkill.build_branch_name("PROJ-200")
        assert result == "feature/proj-200-scaffolder"

    def test_sanitizes_special_characters(self) -> None:
        result = ApplyScaffoldDeliverySkill.build_branch_name("PROJ-300", "hello world!@#")
        assert "!" not in result
        assert "@" not in result
        assert "#" not in result
