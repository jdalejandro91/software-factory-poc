"""Unit tests — ScaffoldingPromptBuilder (hardened prompt with XML delimiters)."""

import json

from software_factory_poc.core.application.skills.scaffold.prompt_templates.scaffolding_prompt_builder import (
    ScaffoldingPromptBuilder,
)
from software_factory_poc.core.domain.mission import Mission, TaskDescription


def _make_mission() -> Mission:
    return Mission(
        id="1001",
        key="PROJ-101",
        summary="Create payment microservice",
        status="To Do",
        project_key="PROJ",
        issue_type="Story",
        description=TaskDescription(
            raw_content="We need a payment service with Stripe integration.",
            config={
                "technology_stack": "Python/FastAPI",
                "parameters": {
                    "service_name": "payment-service",
                    "description": "Handles payments",
                    "owner_team": "payments-team",
                },
                "target": {
                    "gitlab_project_path": "org/payment-service",
                    "branch_slug": "feature/proj-101-payment",
                },
            },
        ),
    )


BUILDER = ScaffoldingPromptBuilder()
CONTEXT = "Hexagonal architecture with src/domain, src/application, src/infrastructure."


class TestMandatorySections:
    """All 7 mandatory sections must be present in the generated prompt."""

    def test_role_section_present(self) -> None:
        prompt = BUILDER.build_prompt_from_mission(_make_mission(), CONTEXT)
        assert "## ROLE" in prompt

    def test_goal_section_present(self) -> None:
        prompt = BUILDER.build_prompt_from_mission(_make_mission(), CONTEXT)
        assert "## GOAL" in prompt

    def test_input_data_section_present(self) -> None:
        prompt = BUILDER.build_prompt_from_mission(_make_mission(), CONTEXT)
        assert "## INPUT DATA" in prompt

    def test_architecture_context_section_present(self) -> None:
        prompt = BUILDER.build_prompt_from_mission(_make_mission(), CONTEXT)
        assert "## ARCHITECTURE CONTEXT" in prompt

    def test_hard_constraints_section_present(self) -> None:
        prompt = BUILDER.build_prompt_from_mission(_make_mission(), CONTEXT)
        assert "## HARD CONSTRAINTS" in prompt

    def test_output_schema_section_present(self) -> None:
        prompt = BUILDER.build_prompt_from_mission(_make_mission(), CONTEXT)
        assert "## OUTPUT SCHEMA" in prompt

    def test_anti_examples_section_present(self) -> None:
        prompt = BUILDER.build_prompt_from_mission(_make_mission(), CONTEXT)
        assert "## ANTI-EXAMPLES" in prompt


class TestXmlDelimiters:
    """User-supplied data must be wrapped in XML delimiters."""

    def test_jira_summary_delimiter(self) -> None:
        prompt = BUILDER.build_prompt_from_mission(_make_mission(), CONTEXT)
        assert "<jira_summary>" in prompt
        assert "</jira_summary>" in prompt
        assert "<jira_summary>Create payment microservice</jira_summary>" in prompt

    def test_jira_description_delimiter(self) -> None:
        prompt = BUILDER.build_prompt_from_mission(_make_mission(), CONTEXT)
        assert "<jira_description>" in prompt
        assert "</jira_description>" in prompt

    def test_mission_config_delimiter(self) -> None:
        prompt = BUILDER.build_prompt_from_mission(_make_mission(), CONTEXT)
        assert "<mission_config>" in prompt
        assert "</mission_config>" in prompt

    def test_architecture_context_delimiter(self) -> None:
        prompt = BUILDER.build_prompt_from_mission(_make_mission(), CONTEXT)
        assert "<architecture_context>" in prompt
        assert "</architecture_context>" in prompt
        assert f"<architecture_context>{CONTEXT}</architecture_context>" in prompt


class TestSchemaReference:
    """Prompt must reference ScaffoldingResponseSchema with parseable example."""

    def test_schema_name_referenced(self) -> None:
        prompt = BUILDER.build_prompt_from_mission(_make_mission(), CONTEXT)
        assert "ScaffoldingResponseSchema" in prompt

    def test_schema_fields_mentioned(self) -> None:
        prompt = BUILDER.build_prompt_from_mission(_make_mission(), CONTEXT)
        assert "branch_name" in prompt
        assert "commit_message" in prompt
        assert "files" in prompt
        assert "FileSchemaDTO" in prompt

    def test_json_example_is_parseable(self) -> None:
        prompt = BUILDER.build_prompt_from_mission(_make_mission(), CONTEXT)
        start = prompt.index("```json\n") + len("```json\n")
        end = prompt.index("\n```", start)
        example_json = prompt[start:end]
        parsed = json.loads(example_json)
        assert "branch_name" in parsed
        assert "commit_message" in parsed
        assert isinstance(parsed["files"], list)


class TestMissionFieldsIncluded:
    """Prompt must include key Mission fields beyond just summary."""

    def test_mission_key_included(self) -> None:
        prompt = BUILDER.build_prompt_from_mission(_make_mission(), CONTEXT)
        assert "PROJ-101" in prompt

    def test_project_key_included(self) -> None:
        prompt = BUILDER.build_prompt_from_mission(_make_mission(), CONTEXT)
        assert "PROJ" in prompt

    def test_issue_type_included(self) -> None:
        prompt = BUILDER.build_prompt_from_mission(_make_mission(), CONTEXT)
        assert "Story" in prompt

    def test_tech_stack_included(self) -> None:
        prompt = BUILDER.build_prompt_from_mission(_make_mission(), CONTEXT)
        assert "Python/FastAPI" in prompt

    def test_service_name_included(self) -> None:
        prompt = BUILDER.build_prompt_from_mission(_make_mission(), CONTEXT)
        assert "payment-service" in prompt

    def test_fallback_service_name_uses_key(self) -> None:
        mission = _make_mission()
        mission.description.config["parameters"] = {}
        prompt = BUILDER.build_prompt_from_mission(mission, CONTEXT)
        assert "PROJ-101" in prompt

    def test_empty_context_uses_fallback(self) -> None:
        prompt = BUILDER.build_prompt_from_mission(_make_mission(), "")
        assert "No specific documentation provided" in prompt
