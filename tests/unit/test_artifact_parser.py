import json

import pytest

from software_factory_poc.core.application.skills.scaffold.prompt_templates.scaffolding_prompt_builder import (
    ScaffoldingPromptBuilder,
)
from software_factory_poc.core.domain.mission import Mission, TaskDescription


class TestScaffoldingPromptBuilder:
    @pytest.fixture
    def prompt_builder(self):
        return ScaffoldingPromptBuilder()

    @pytest.fixture
    def sample_mission(self):
        description = TaskDescription(
            raw_content="Raw content", config={"technology_stack": "Python/FastAPI"}
        )
        return Mission(
            id="1001",
            key="TEST-123",
            summary="Create a simple Python API",
            status="INITIAL",
            project_key="TEST",
            issue_type="Story",
            description=description,
        )

    def test_build_prompt_basic_flow(self, prompt_builder, sample_mission):
        """Test that prompt is generated with all sections."""
        context = "Use modular structure."
        system, user = prompt_builder.build_prompt_from_mission(sample_mission, context)

        assert "<system_role>" in system
        assert "BrahMAS Sovereign Scaffolder" in system
        assert "<architecture_standards>" in user
        assert "Use modular structure" in user
        assert "Python/FastAPI" in system

    def test_build_prompt_empty_context(self, prompt_builder, sample_mission):
        """Test prompt generation fallback when context is missing."""
        _, user = prompt_builder.build_prompt_from_mission(sample_mission, "")

        assert "No specific documentation provided" in user

    def test_json_example_is_parseable(self, prompt_builder, sample_mission):
        """Test that the example JSON in the output schema is valid."""
        system, _ = prompt_builder.build_prompt_from_mission(sample_mission, "some context")
        start = system.index("```json\n") + len("```json\n")
        end = system.index("\n```", start)
        example_json = system[start:end]
        parsed = json.loads(example_json)
        assert "branch_name" in parsed
        assert "files" in parsed
