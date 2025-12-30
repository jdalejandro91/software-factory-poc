from unittest.mock import AsyncMock, MagicMock

import pytest

from software_factory_poc.application.core.entities.llm_response import LlmResponse
from software_factory_poc.application.core.value_objects.model_id import ModelId
from software_factory_poc.application.core.value_objects.provider_name import ProviderName
from software_factory_poc.application.usecases.knowledge.architecture_knowledge_service import (
    ArchitectureKnowledgeService,
)
from software_factory_poc.application.ports.llms.llm_provider import LlmProvider
from software_factory_poc.application.usecases.scaffolding.genai_scaffolding_service import GenaiScaffoldingService


@pytest.fixture
def mock_knowledge_service():
    service = MagicMock(spec=ArchitectureKnowledgeService)
    service.get_architecture_guidelines.return_value = "Architecture Guidelines Text"
    return service

@pytest.fixture
def mock_llm_provider():
    provider = MagicMock(spec=LlmProvider)
    provider.generate = AsyncMock()
    return provider

@pytest.fixture
def mock_model_id():
    return ModelId(ProviderName.OPENAI, "gpt-4o")

@pytest.mark.asyncio
async def test_generate_scaffolding_success(mock_llm_provider, mock_knowledge_service, mock_model_id):
    # Setup
    service = GenaiScaffoldingService(mock_llm_provider, mock_knowledge_service)
    
    # Mock LLM responses
    planning_response = LlmResponse(model=mock_model_id, content='["src/main.py", "src/utils.py"]')
    coding_response_1 = LlmResponse(model=mock_model_id, content="```python\nprint('main')\n```")
    coding_response_2 = LlmResponse(model=mock_model_id, content="def util(): pass")
    
    mock_llm_provider.generate.side_effect = [
        planning_response,   # Planning
        coding_response_1,   # First file
        coding_response_2    # Second file
    ]

    # Execute
    result = await service.generate_scaffolding("TEST-1", "Make a simple app")

    # Verify
    assert len(result) == 2
    assert result["src/main.py"] == "print('main')"
    assert result["src/utils.py"] == "def util(): pass"
    
    # Verify invocations
    assert mock_llm_provider.generate.call_count == 3
    
    # Verify Knowledge Service called
    mock_knowledge_service.get_architecture_guidelines.assert_called_once()

@pytest.mark.asyncio
async def test_generate_scaffolding_planning_failure(mock_llm_provider, mock_knowledge_service, mock_model_id):
    # Setup
    service = GenaiScaffoldingService(mock_llm_provider, mock_knowledge_service)
    
    # Mock malformed JSON response
    mock_llm_provider.generate.side_effect = [
        LlmResponse(model=mock_model_id, content="Not a JSON")
    ]
    
    # Execute & Verify
    with pytest.raises(Exception): # JSONDecodeError or similar
        await service.generate_scaffolding("TEST-Fail", "Bad output")
