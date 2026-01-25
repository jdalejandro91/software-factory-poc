
import pytest
from unittest.mock import MagicMock
from software_factory_poc.application.core.agents.scaffolding.scaffolding_agent import ScaffoldingAgent
from software_factory_poc.application.core.agents.scaffolding.config.scaffolding_agent_config import ScaffoldingAgentConfig
from software_factory_poc.application.core.agents.scaffolding.value_objects.scaffolding_order import ScaffoldingOrder
from software_factory_poc.infrastructure.providers.vcs.services.gitlab_branch_service import GitLabBranchService

def test_branch_naming_slugification():
    config = MagicMock(spec=ScaffoldingAgentConfig)
    agent = ScaffoldingAgent(config)
    request = ScaffoldingOrder(issue_key="PROJ-123_FIX", summary="", technology_stack="", raw_instruction="")
    
    branch_name = agent._get_branch_name(request)
    assert branch_name == "feature/proj-123fix-scaffolding"

def test_branch_creation_ref_passing():
    config = MagicMock(spec=ScaffoldingAgentConfig)
    config.default_target_branch = "develop"
    agent = ScaffoldingAgent(config)
    
    mock_vcs = MagicMock()
    mock_vcs.resolve_project_id.return_value = 1
    
    request = ScaffoldingOrder(issue_key="A", summary="B", technology_stack="C", raw_instruction="D", repository_url="http://repo")
    
    # Mock prepare artifacts to avoid error
    agent._prepare_commit_payload = MagicMock(return_value={})
    
    agent._apply_changes_to_vcs(request, mock_vcs, [MagicMock()])
    
    mock_vcs.create_branch.assert_called_with(1, "feature/a-scaffolding", ref="develop")

def test_gitlab_service_conflict_handling():
    mock_client = MagicMock()
    service = GitLabBranchService(mock_client)
    
    # Simulate 400/409 error
    error = Exception("Conflict")
    error.response = MagicMock(status_code=409)
    mock_client.post.side_effect = error
    
    # Simulate existing branch check
    mock_client.get.return_value.status_code = 200
    mock_client.get.return_value.json.return_value = {"name": "main"}
    
    result = service.create_branch(1, "main")
    
    assert result == {"name": "main"}
