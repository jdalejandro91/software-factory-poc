
import pytest
from unittest.mock import MagicMock, patch
from software_factory_poc.application.core.agents.scaffolding.scaffolding_agent import ScaffoldingAgent
from software_factory_poc.application.core.agents.scaffolding.config.scaffolding_agent_config import ScaffoldingAgentConfig
from software_factory_poc.application.core.agents.scaffolding.value_objects.scaffolding_order import ScaffoldingOrder
from software_factory_poc.application.core.agents.common.config.task_status import TaskStatus
from software_factory_poc.application.core.agents.reporter.config.reporter_constants import ReporterMessages
from software_factory_poc.infrastructure.providers.vcs.services.gitlab_branch_service import GitLabBranchService

@pytest.fixture
def mock_config():
    config = MagicMock(spec=ScaffoldingAgentConfig)
    config.project_allowlist = ["group"]
    config.model_name = "gpt-4"
    config.default_target_branch = "main"
    return config

def test_scaffolding_agent_short_circuit_on_existing_branch(mock_config):
    # Setup
    agent = ScaffoldingAgent(mock_config)
    
    mock_reporter = MagicMock()
    mock_vcs = MagicMock()
    
    request = ScaffoldingOrder(
        issue_key="TEST-1",
        raw_instruction="gitlab_project_path: 'group/project'",
        repository_url="http://gitlab.com/group/project.git"
    )
    
    # Mock VCS behavior
    mock_vcs.resolve_project_id.return_value = 123
    # validate_branch returns URL if exists
    mock_vcs.validate_branch.return_value = "http://gitlab.com/group/project/-/tree/feature/TEST-1-scaffolding"
    
    # Mock permissions passing
    with patch.object(agent, '_check_permissions'):
        # Execute
        result = agent._start_task_execution(request, mock_reporter, mock_vcs)
        
    # Verify Short Circuit
    assert result is True
    
    # Verify Reporting
    mock_reporter.report_success.assert_called_once()
    args, _ = mock_reporter.report_success.call_args
    assert ReporterMessages.BRANCH_EXISTS_PREFIX in args[1]
    
    # Verify Transition
    mock_reporter.transition_task.assert_called_once_with("TEST-1", TaskStatus.IN_REVIEW)

def test_gitlab_branch_service_404_handling():
    mock_client = MagicMock()
    service = GitLabBranchService(mock_client)
    
    # Case 1: 404
    mock_response_404 = MagicMock()
    mock_response_404.status_code = 404
    mock_client.get.return_value = mock_response_404
    
    assert service.branch_exists(1, "missing-branch") is False
    
    # Case 2: 200
    mock_response_200 = MagicMock()
    mock_response_200.status_code = 200
    mock_client.get.return_value = mock_response_200
    
    assert service.branch_exists(1, "existing-branch") is True
