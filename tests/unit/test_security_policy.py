import pytest
from unittest.mock import MagicMock
from software_factory_poc.application.core.agents.scaffolding.scaffolding_agent import ScaffoldingAgent
from software_factory_poc.application.core.agents.scaffolding.config.scaffolding_agent_config import ScaffoldingAgentConfig
from software_factory_poc.application.core.agents.scaffolding.value_objects.scaffolding_order import ScaffoldingOrder
from software_factory_poc.application.core.agents.common.config.task_status import TaskStatus

# Helper to create order with description
def create_order(instruction: str):
    return ScaffoldingOrder(
        issue_key="KAN-1",
        raw_instruction=instruction,
        summary="Test"
    )

def test_check_permissions_allowed():
    config = MagicMock(spec=ScaffoldingAgentConfig)
    config.project_allowlist = ["allowed-group"]
    config.model_name = "gpt-4"
    agent = ScaffoldingAgent(config)
    
    instruction = """
    target:
      gitlab_project_path: 'allowed-group/project'
    """
    request = create_order(instruction)
    
    # Should not raise
    agent._check_permissions(request)

def test_check_permissions_denied():
    config = MagicMock(spec=ScaffoldingAgentConfig)
    config.project_allowlist = ["allowed-group"]
    agent = ScaffoldingAgent(config)
    
    instruction = """
    target:
      gitlab_project_path: 'hacker-group/project'
    """
    request = create_order(instruction)
    
    with pytest.raises(PermissionError) as exc:
        agent._check_permissions(request)
    assert "Security Policy Violation" in str(exc.value)

def test_check_permissions_no_config_insecure():
    config = MagicMock(spec=ScaffoldingAgentConfig)
    config.project_allowlist = [] # Empty
    agent = ScaffoldingAgent(config)
    
    instruction = "gitlab_project_path: 'any-group/project'"
    request = create_order(instruction)
    
    # Should pass with warning
    agent._check_permissions(request)

def test_check_permissions_no_path_found():
    config = MagicMock(spec=ScaffoldingAgentConfig)
    config.project_allowlist = ["group"]
    agent = ScaffoldingAgent(config)
    
    instruction = "No path here"
    request = create_order(instruction)
    
    with pytest.raises(ValueError) as exc:
        agent._check_permissions(request)
    assert "Could not identify" in str(exc.value)
