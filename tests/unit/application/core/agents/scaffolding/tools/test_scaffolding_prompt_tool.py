from unittest.mock import patch
from software_factory_poc.application.core.agents.scaffolding.tools.scaffolding_prompt_builder import ScaffoldingPromptBuilder
from software_factory_poc.application.core.agents.scaffolding.scaffolding_order import ScaffoldingOrder
from unittest.mock import patch

from software_factory_poc.application.core.agents.scaffolding.scaffolding_order import ScaffoldingOrder

from software_factory_poc.application.core.agents.scaffolding.tools.scaffolding_prompt_builder import \
    ScaffoldingPromptBuilder


class TestScaffoldingPromptTool:
    @patch('software_factory_poc.application.core.agents.scaffolding.tools.scaffolding_prompt_builder.logger')
    def test_build_prompt_basic(self, mock_logger):
         # Setup
        request = ScaffoldingOrder(
            issue_key="PROJ-123",
            summary="Build API",
            raw_instruction="Make it fast",
            reporter="User",
            repository_url="http://repo",
            technology_stack="python"
        )
        context = "Use Clean Architecture"
        
        tool = ScaffoldingPromptBuilder()
        prompt = tool.build_prompt(request, context)
        
        assert "PROJ-123" in prompt
        assert "Build API" in prompt
        assert "Use Clean Architecture" in prompt
        assert "python" in prompt

    def test_build_prompt_empty_context(self):
         # Setup
        request = ScaffoldingOrder(
            issue_key="PROJ-123",
            summary="Build API",
            raw_instruction="Make it fast",
            reporter="User",
            repository_url="http://repo",
            technology_stack="python"
        )
        tool = ScaffoldingPromptBuilder()
        prompt = tool.build_prompt(request, "")
        
        assert "PROJ-123" in prompt
        # Should NOT fail, just build prompt with empty context or fallback
        assert "No specific architecture documentation provided" in prompt or "ARCHITECTURAL STANDARDS" in prompt
