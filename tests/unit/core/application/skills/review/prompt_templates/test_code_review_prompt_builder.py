"""Unit tests — CodeReviewPromptBuilder (El Verdugo template)."""

import json

from software_factory_poc.core.application.skills.review.prompt_templates.code_review_prompt_builder import (
    CodeReviewPromptBuilder,
)
from software_factory_poc.core.domain.mission import Mission, TaskDescription

BUILDER = CodeReviewPromptBuilder()


def _make_mission() -> Mission:
    return Mission(
        id="20001",
        key="PROJ-200",
        summary="Review MR for authentication module",
        status="In Progress",
        project_key="PROJ",
        issue_type="Code Review",
        description=TaskDescription(
            raw_content="Review the auth module MR with OWASP focus.",
            config={
                "code_review_params": {
                    "review_request_url": "https://gitlab.example.com/merge_requests/55",
                    "gitlab_project_id": "42",
                    "source_branch_name": "feature/proj-200-auth",
                },
            },
        ),
    )


MR_DIFF = "diff --git a/src/auth.py b/src/auth.py\n+def login(): pass"
CONVENTIONS = "Follow hexagonal architecture and SOLID principles."
CR_PARAMS: dict[str, str] = {
    "mr_url": "https://gitlab.example.com/merge_requests/55",
    "project_id": "42",
    "branch": "feature/proj-200-auth",
    "mr_iid": "55",
}


def _build_user_prompt() -> str:
    return BUILDER.build_analysis_prompt(
        mission=_make_mission(),
        mr_diff=MR_DIFF,
        conventions=CONVENTIONS,
        code_review_params=CR_PARAMS,
    )


class TestSystemPrompt:
    """System prompt must contain El Verdugo template elements."""

    def test_system_prompt_not_empty(self) -> None:
        assert len(BUILDER.build_system_prompt().strip()) > 0

    def test_system_prompt_contains_system_role(self) -> None:
        sys_prompt = BUILDER.build_system_prompt()
        assert "<system_role>" in sys_prompt
        assert "</system_role>" in sys_prompt

    def test_system_prompt_contains_strict_rules(self) -> None:
        sys_prompt = BUILDER.build_system_prompt()
        assert "<strict_rules>" in sys_prompt
        assert "</strict_rules>" in sys_prompt

    def test_system_prompt_mentions_brahmas(self) -> None:
        assert "BrahMAS" in BUILDER.build_system_prompt()

    def test_system_prompt_mentions_quality_gatekeeper(self) -> None:
        assert "Quality Gatekeeper" in BUILDER.build_system_prompt()


class TestMandatorySections:
    """All mandatory sections must be present in the user prompt."""

    def test_mission_requirements_present(self) -> None:
        prompt = _build_user_prompt()
        assert "<mission_requirements>" in prompt
        assert "</mission_requirements>" in prompt

    def test_architecture_standards_present(self) -> None:
        prompt = _build_user_prompt()
        assert "<architecture_standards>" in prompt
        assert "</architecture_standards>" in prompt

    def test_merge_request_diffs_present(self) -> None:
        prompt = _build_user_prompt()
        assert "<merge_request_diffs>" in prompt
        assert "</merge_request_diffs>" in prompt

    def test_final_instruction_present(self) -> None:
        assert "INSTRUCCION" in _build_user_prompt()

    def test_output_schema_in_system(self) -> None:
        system = BUILDER.build_system_prompt()
        assert "<output_schema>" in system
        assert "</output_schema>" in system

    def test_anti_examples_in_system(self) -> None:
        system = BUILDER.build_system_prompt()
        assert "<anti_examples>" in system
        assert "</anti_examples>" in system


class TestXmlDelimiters:
    """User-supplied data must be wrapped in XML delimiters."""

    def test_jira_summary_delimiter(self) -> None:
        prompt = _build_user_prompt()
        assert "<jira_summary>" in prompt
        assert "</jira_summary>" in prompt

    def test_jira_description_delimiter(self) -> None:
        prompt = _build_user_prompt()
        assert "<jira_description>" in prompt
        assert "</jira_description>" in prompt

    def test_merge_request_diffs_delimiter(self) -> None:
        prompt = _build_user_prompt()
        assert "<merge_request_diffs>" in prompt
        assert "</merge_request_diffs>" in prompt

    def test_architecture_standards_delimiter(self) -> None:
        prompt = _build_user_prompt()
        assert "<architecture_standards>" in prompt
        assert "</architecture_standards>" in prompt


class TestSchemaReference:
    """System prompt must reference CodeReviewResponseSchema with parseable example."""

    def test_schema_name_referenced(self) -> None:
        assert "CodeReviewResponseSchema" in BUILDER.build_system_prompt()

    def test_schema_fields_mentioned(self) -> None:
        sys_prompt = BUILDER.build_system_prompt()
        assert "is_approved" in sys_prompt
        assert "summary" in sys_prompt
        assert "issues" in sys_prompt
        assert "CodeIssueSchema" in sys_prompt

    def test_json_example_is_parseable(self) -> None:
        sys_prompt = BUILDER.build_system_prompt()
        start = sys_prompt.index("```json\n") + len("```json\n")
        end = sys_prompt.index("\n```", start)
        example_json = sys_prompt[start:end]
        parsed = json.loads(example_json)
        assert "is_approved" in parsed
        assert "summary" in parsed
        assert isinstance(parsed["issues"], list)


class TestMissionFieldsIncluded:
    """Prompt must include key Mission fields for context."""

    def test_mission_key_included(self) -> None:
        assert "PROJ-200" in _build_user_prompt()

    def test_project_key_included(self) -> None:
        assert "PROJ" in _build_user_prompt()

    def test_issue_type_included(self) -> None:
        assert "Code Review" in _build_user_prompt()

    def test_mr_url_included(self) -> None:
        assert "https://gitlab.example.com/merge_requests/55" in _build_user_prompt()

    def test_branch_included(self) -> None:
        assert "feature/proj-200-auth" in _build_user_prompt()

    def test_repository_tree_included_when_provided(self) -> None:
        prompt = BUILDER.build_analysis_prompt(
            mission=_make_mission(),
            mr_diff=MR_DIFF,
            conventions=CONVENTIONS,
            code_review_params=CR_PARAMS,
            repository_tree="src/\n  auth.py\n  main.py",
        )
        assert "<repository_tree>" in prompt
        assert "auth.py" in prompt

    def test_repository_tree_absent_when_empty(self) -> None:
        prompt = _build_user_prompt()
        assert "<repository_tree>" not in prompt
