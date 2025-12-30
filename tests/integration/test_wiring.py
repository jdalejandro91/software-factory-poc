from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from software_factory_poc.application.core.domain.configuration.knowledge_provider_type import (
    KnowledgeProviderType,
)
from software_factory_poc.application.core.domain.configuration.task_tracker_type import (
    TaskTrackerType,
)
from software_factory_poc.application.core.domain.configuration.vcs_provider_type import (
    VcsProviderType,
)
from software_factory_poc.application.core.domain.configuration.llm_provider_type import (
    LlmProviderType,
)
from software_factory_poc.application.core.domain.value_objects.model_id import ModelId
from software_factory_poc.application.core.domain.configuration.scaffolding_agent_config import (
    ScaffoldingAgentConfig,
)
from software_factory_poc.application.core.domain.entities.scaffolding.scaffolding_request import (
    ScaffoldingRequest,
)
from software_factory_poc.application.usecases.scaffolding.create_scaffolding_usecase import (
    CreateScaffoldingUseCase,
)
from software_factory_poc.infrastructure.resolution.provider_resolver import ProviderResolver


@pytest.fixture
def dummy_config():
    return ScaffoldingAgentConfig(
        llm_priority_list=[
            ModelId(provider=LlmProviderType.OPENAI, name="gpt-4-test"),
            ModelId(provider=LlmProviderType.DEEPSEEK, name="deepseek-test")
        ],
        vcs_provider=VcsProviderType.GITLAB,
        tracker_provider=TaskTrackerType.JIRA,
        knowledge_provider=KnowledgeProviderType.CONFLUENCE,
        enable_secure_mode=True,
        work_dir=Path("/tmp/test")
    )

def test_use_case_initialization_and_execution_flow(dummy_config):
    # Mock Resolver to avoid real heavy lifting in unit test
    mock_resolver = MagicMock(spec=ProviderResolver)
    
    # Mock Gateways
    mock_vcs = MagicMock()
    mock_tracker = MagicMock()
    mock_llm = MagicMock()
    
    mock_resolver.resolve_vcs.return_value = mock_vcs
    mock_resolver.resolve_tracker.return_value = mock_tracker
    mock_resolver.resolve_llm_gateway.return_value = mock_llm
    
    # Configure VCS to say branch does NOT exist
    mock_vcs.resolve_project_id.return_value = "101"
    mock_vcs.branch_exists.return_value = False
    
    # Instantiate Use Case
    use_case = CreateScaffoldingUseCase(dummy_config, mock_resolver)
    
    # Create Request
    request = ScaffoldingRequest(
        issue_key="TEST-123",
        raw_instruction="Make a Flask app",
        technology_stack="Python",
        repository_url="http://gitlab/repo",
        project_id="101"
    )
    
    # Mock LLM response to be parsed
    mock_llm.generate_code.return_value = "<<<FILE:app.py>>>\nprint('hello')\n<<<END>>>"
    
    # Execute
    use_case.execute(request)
    
    # Initial Assertions
    mock_resolver.resolve_vcs.assert_called_once()
    mock_resolver.resolve_llm_gateway.assert_called_once()
    
    # Verify LLM was called with the hint from Config 
    # (The use case logic picks the first model from priority list as hint)
    from unittest.mock import ANY
    mock_llm.generate_code.assert_called_with(
        prompt=ANY, # Prompt uses keyword arg in code
        model=dummy_config.llm_priority_list[0]     # Hint model object
    )
    
    # Verify VCS was called
    mock_vcs.create_merge_request.assert_called()
    
    # Verify Tracker notified
    mock_tracker.add_comment.assert_called()
    mock_tracker.transition_status.assert_called() # Also verifying transition
    from software_factory_poc.application.core.ports.gateways.llm_gateway import LlmGateway
    from software_factory_poc.application.core.domain.configuration.task_status import TaskStatus
    mock_tracker.transition_status.assert_called_with("TEST-123", TaskStatus.IN_REVIEW)

def test_resolver_logic_fails_for_unsupported_provider():
    # Config with GITHUB (Not Implemented)
    config = ScaffoldingAgentConfig(
        llm_priority_list=[],
        vcs_provider=VcsProviderType.GITHUB, # Unsupported
        tracker_provider=TaskTrackerType.JIRA,
        knowledge_provider=KnowledgeProviderType.CONFLUENCE,
        enable_secure_mode=True,
        work_dir=Path("/tmp")
    )
    
    # We use a real resolver here (with mocked settings) to test the factory logic
    mock_settings = MagicMock()
    resolver = ProviderResolver(config, mock_settings)
    
    with pytest.raises(NotImplementedError) as excinfo:
        resolver.resolve_vcs()
    
    assert "GitHub adapter is not yet implemented" in str(excinfo.value)

def test_resolver_wires_gitlab_correctly(dummy_config):
    # Testing that it attempts to import and verify settings for GitLab
    mock_settings = MagicMock()
    mock_settings.gitlab_token = "secret"
    mock_settings.gitlab_base_url = "https://gitlab.com"
    
    resolver = ProviderResolver(dummy_config, mock_settings)
    
    # We mock the internal imports or just check the result type if imports are available
    # Since we are in the real environment, we can check if it returns a GitLabProviderImpl
    # provided dependencies can be satisfied or mocked.
    
    # To avoid network calls in __init__ of adapters (like validate_credentials), 
    # we might need to rely on the fact that our factories use dependency injection.
    
    # Let's try to resolve and assert the type.
    # Note: GitLabHttpClient does validation in __init__ which might fail if env vars not set?
    # We mocked settings so it should pass validation if logic uses settings.
    
    with patch("software_factory_poc.infrastructure.providers.vcs.clients.gitlab_http_client.GitLabHttpClient._validate_config"):
        vcs = resolver.resolve_vcs()
        assert vcs.__class__.__name__ == "GitLabProviderImpl"
