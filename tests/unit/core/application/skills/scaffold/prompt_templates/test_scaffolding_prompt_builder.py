"""Unit tests — ScaffoldingPromptBuilder (system + user prompt with XML delimiters)."""

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


def _build() -> tuple[str, str]:
    return BUILDER.build_prompt_from_mission(_make_mission(), CONTEXT)


class TestReturnType:
    """build_prompt_from_mission must return a (system, user) tuple."""

    def test_returns_tuple_of_two_strings(self) -> None:
        result = _build()
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], str)
        assert isinstance(result[1], str)


class TestSystemPromptSections:
    """System prompt must contain role, rules, schema, and anti-examples."""

    def test_system_role_section_present(self) -> None:
        system, _ = _build()
        assert "<system_role>" in system
        assert "</system_role>" in system
        assert "BrahMAS Sovereign Scaffolder" in system

    def test_strict_rules_section_present(self) -> None:
        system, _ = _build()
        assert "<strict_rules>" in system
        assert "</strict_rules>" in system

    def test_output_schema_section_present(self) -> None:
        system, _ = _build()
        assert "<output_schema>" in system
        assert "</output_schema>" in system

    def test_anti_examples_section_present(self) -> None:
        system, _ = _build()
        assert "<anti_examples>" in system
        assert "</anti_examples>" in system

    def test_tech_stack_in_system_role(self) -> None:
        system, _ = _build()
        assert "Python/FastAPI" in system


class TestUserPromptSections:
    """User prompt must contain mission intent, tech stack, and architecture."""

    def test_mission_intent_section_present(self) -> None:
        _, user = _build()
        assert "<mission_intent>" in user
        assert "</mission_intent>" in user

    def test_technology_stack_section_present(self) -> None:
        _, user = _build()
        assert "<technology_stack>" in user
        assert "</technology_stack>" in user

    def test_architecture_standards_section_present(self) -> None:
        _, user = _build()
        assert "<architecture_standards>" in user
        assert "</architecture_standards>" in user


class TestXmlDelimiters:
    """User-supplied data must be wrapped in XML delimiters."""

    def test_jira_summary_delimiter(self) -> None:
        _, user = _build()
        assert "<jira_summary>Create payment microservice</jira_summary>" in user

    def test_jira_description_delimiter(self) -> None:
        _, user = _build()
        assert "<jira_description>" in user
        assert "</jira_description>" in user

    def test_architecture_context_delimiter(self) -> None:
        _, user = _build()
        assert "<architecture_context>" in user
        assert "</architecture_context>" in user
        assert f"<architecture_context>{CONTEXT}</architecture_context>" in user


class TestSchemaReference:
    """System prompt must reference ScaffoldingResponseSchema with parseable example."""

    def test_schema_name_referenced(self) -> None:
        system, _ = _build()
        assert "ScaffoldingResponseSchema" in system

    def test_schema_fields_mentioned(self) -> None:
        system, _ = _build()
        assert "branch_name" in system
        assert "commit_message" in system
        assert "files" in system
        assert "FileSchemaDTO" in system

    def test_json_example_is_parseable(self) -> None:
        system, _ = _build()
        start = system.index("```json\n") + len("```json\n")
        end = system.index("\n```", start)
        example_json = system[start:end]
        parsed = json.loads(example_json)
        assert "branch_name" in parsed
        assert "commit_message" in parsed
        assert isinstance(parsed["files"], list)


class TestMissionFieldsIncluded:
    """User prompt must include key Mission fields beyond just summary."""

    def test_mission_key_included(self) -> None:
        _, user = _build()
        assert "PROJ-101" in user

    def test_project_key_included(self) -> None:
        _, user = _build()
        assert "PROJ" in user

    def test_issue_type_included(self) -> None:
        _, user = _build()
        assert "Story" in user

    def test_tech_stack_included(self) -> None:
        _, user = _build()
        assert "Python/FastAPI" in user

    def test_service_name_included(self) -> None:
        _, user = _build()
        assert "payment-service" in user

    def test_fallback_service_name_uses_key(self) -> None:
        mission = _make_mission()
        mission.description.config["parameters"] = {}
        _, user = BUILDER.build_prompt_from_mission(mission, CONTEXT)
        assert "PROJ-101" in user

    def test_empty_context_uses_fallback(self) -> None:
        _, user = BUILDER.build_prompt_from_mission(_make_mission(), "")
        assert "No specific documentation provided" in user
