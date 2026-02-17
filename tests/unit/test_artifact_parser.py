import pytest

from software_factory_poc.core.application.agents.scaffolder.prompt_templates.scaffolding_prompt_builder import (
    ScaffoldingPromptBuilder,
)
from software_factory_poc.core.domain.mission.entities.mission import Mission
from software_factory_poc.core.domain.mission.value_objects.task_description import TaskDescription


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
        prompt = prompt_builder.build_prompt_from_mission(sample_mission, context)

        assert "ROLE: You are a Principal Software Architect" in prompt
        assert "SOURCE OF TRUTH" in prompt
        assert "Use modular structure" in prompt
        assert "TASK SPECIFICATION" in prompt
        assert "Python/FastAPI" in prompt

    def test_build_prompt_empty_context(self, prompt_builder, sample_mission):
        """Test prompt generation fallback when context is missing."""
        prompt = prompt_builder.build_prompt_from_mission(sample_mission, "")

        assert "No specific documentation provided" in prompt

    def test_json_example_formatting(self, prompt_builder):
        """Test that the example JSON is valid JSON structure in the text."""
        example = prompt_builder._get_example_output()
        assert "JSON OUTPUT EXAMPLE" in example
        assert "path" in example
        assert "content" in example
