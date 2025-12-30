
import pytest
from unittest.mock import MagicMock, patch
from software_factory_poc.application.core.domain.services.prompt_builder_service import PromptBuilderService
from software_factory_poc.application.core.domain.entities.scaffolding.scaffolding_request import ScaffoldingRequest

class TestPromptBuilderService:
    @patch('software_factory_poc.application.core.domain.services.prompt_builder_service.logger')
    def test_build_scaffolding_prompt_structure_and_logging(self, mock_logger):
        # Setup
        request = ScaffoldingRequest(
            issue_key="PROJ-123",
            summary="Build API",
            raw_instruction="Make it fast",
            reporter="User",
            technology_stack="python"
        )
        context = "Use Clean Architecture"

        # Execute
        prompt = PromptBuilderService.build_scaffolding_prompt(request, context)

        # Verify Structure
        assert "ROLE: You are an Expert Software Architect" in prompt
        assert "--- ARCHITECTURAL STANDARDS (RAG CONTEXT) ---" in prompt
        assert "Use Clean Architecture" in prompt
        assert "<<<FILE:path/to/file.ext>>>" in prompt # Format instruction
        assert "PROJ-123" in prompt

        # Verify Logging
        mock_logger.info.assert_called()
        log_args = mock_logger.info.call_args[0][0]
        assert "--- [DEBUG] FULL GENERATED PROMPT (PROJ-123) ---" in log_args
        assert prompt in log_args

    @patch('software_factory_poc.application.core.domain.services.prompt_builder_service.logger')
    def test_build_scaffolding_prompt_empty_context_warning(self, mock_logger):
        request = ScaffoldingRequest(
            issue_key="PROJ-123",
            summary="Build API",
            raw_instruction="Make it fast",
            reporter="User",
            technology_stack="python"
        )
        # Empty context
        prompt = PromptBuilderService.build_scaffolding_prompt(request, "")

        # Verify Warning
        mock_logger.warning.assert_called_with("Generating prompt for PROJ-123 WITHOUT Knowledge Context (Empty RAG).")
        # Verify fallback text in prompt
        assert "No specific architecture documentation provided. Use standard best practices." in prompt
