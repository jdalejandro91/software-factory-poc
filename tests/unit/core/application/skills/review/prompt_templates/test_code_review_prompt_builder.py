"""Unit tests — CodeReviewPromptBuilder (hardened prompt with XML delimiters)."""

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


def _build_prompt() -> str:
    return BUILDER.build_analysis_prompt(
        mission=_make_mission(),
        mr_diff=MR_DIFF,
        conventions=CONVENTIONS,
        code_review_params=CR_PARAMS,
    )


class TestSystemPrompt:
    """System prompt must be in English and non-empty."""

    def test_system_prompt_not_empty(self) -> None:
        sys_prompt = BUILDER.build_system_prompt()
        assert len(sys_prompt.strip()) > 0

    def test_system_prompt_in_english(self) -> None:
        sys_prompt = BUILDER.build_system_prompt()
        assert "Senior Software Architect" in sys_prompt

    def test_system_prompt_mentions_brahmas(self) -> None:
        sys_prompt = BUILDER.build_system_prompt()
        assert "BrahMAS" in sys_prompt


class TestMandatorySections:
    """All mandatory sections must be present in the analysis prompt."""

    def test_goal_section_present(self) -> None:
        assert "## GOAL" in _build_prompt()

    def test_evaluation_dimensions_present(self) -> None:
        assert "## EVALUATION DIMENSIONS" in _build_prompt()

    def test_constraints_present(self) -> None:
        assert "## CONSTRAINTS" in _build_prompt()

    def test_output_schema_present(self) -> None:
        assert "## OUTPUT SCHEMA" in _build_prompt()

    def test_anti_examples_present(self) -> None:
        assert "## ANTI-EXAMPLES" in _build_prompt()


class TestXmlDelimiters:
    """User-supplied data must be wrapped in XML delimiters."""

    def test_jira_summary_delimiter(self) -> None:
        prompt = _build_prompt()
        assert "<jira_summary>" in prompt
        assert "</jira_summary>" in prompt

    def test_jira_description_delimiter(self) -> None:
        prompt = _build_prompt()
        assert "<jira_description>" in prompt
        assert "</jira_description>" in prompt

    def test_mr_diff_delimiter(self) -> None:
        prompt = _build_prompt()
        assert "<mr_diff>" in prompt
        assert "</mr_diff>" in prompt

    def test_conventions_delimiter(self) -> None:
        prompt = _build_prompt()
        assert "<conventions>" in prompt
        assert "</conventions>" in prompt


class TestSchemaReference:
    """Prompt must reference CodeReviewResponseSchema with parseable example."""

    def test_schema_name_referenced(self) -> None:
        assert "CodeReviewResponseSchema" in _build_prompt()

    def test_schema_fields_mentioned(self) -> None:
        prompt = _build_prompt()
        assert "is_approved" in prompt
        assert "summary" in prompt
        assert "issues" in prompt
        assert "CodeIssueSchema" in prompt

    def test_json_example_is_parseable(self) -> None:
        prompt = _build_prompt()
        start = prompt.index("```json\n") + len("```json\n")
        end = prompt.index("\n```", start)
        example_json = prompt[start:end]
        parsed = json.loads(example_json)
        assert "is_approved" in parsed
        assert "summary" in parsed
        assert isinstance(parsed["issues"], list)


class TestMissionFieldsIncluded:
    """Prompt must include key Mission fields for context."""

    def test_mission_key_included(self) -> None:
        assert "PROJ-200" in _build_prompt()

    def test_project_key_included(self) -> None:
        assert "PROJ" in _build_prompt()

    def test_issue_type_included(self) -> None:
        assert "Code Review" in _build_prompt()

    def test_mr_url_included(self) -> None:
        prompt = _build_prompt()
        assert "https://gitlab.example.com/merge_requests/55" in prompt

    def test_branch_included(self) -> None:
        assert "feature/proj-200-auth" in _build_prompt()
