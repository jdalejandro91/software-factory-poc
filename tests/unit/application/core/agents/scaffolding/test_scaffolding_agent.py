from unittest.mock import MagicMock, ANY, patch

import pytest
from software_factory_poc.application.core.ports.gateways.dtos import FileContentDTO, MergeRequestDTO, BranchDTO, \
    CommitResultDTO

# Removed duplicate TaskStatus import if it was handled above or keep it
# The original code had: from software_factory_poc.application.core.agents.common.config.task_status import TaskStatus
# I will check if I need to update that one too. I'll leave it for now or update it if I know the path.
from software_factory_poc.application.ports.drivers.common.config.task_status import TaskStatus
from software_factory_poc.application.core.agents.scaffolding.config.scaffolding_agent_config import \
    ScaffoldingAgentConfig
from software_factory_poc.application.core.agents.scaffolding.scaffolding_agent import ScaffoldingAgent
from software_factory_poc.application.core.agents.scaffolding.value_objects.scaffolding_order import \
    ScaffoldingOrder  # Fixed import path


class TestScaffoldingAgent:
    @pytest.fixture
    def mock_tools(self):
        prompt_tool = MagicMock()
        parser_tool = MagicMock()
        return prompt_tool, parser_tool

    @pytest.fixture
    def mock_agents(self):
        reporter = MagicMock()
        vcs = MagicMock()
        researcher = MagicMock()
        reasoner = MagicMock()
        knowledge = MagicMock()
        return reporter, vcs, researcher, reasoner, knowledge

    @pytest.fixture
    def agent(self, mock_tools):
        config = ScaffoldingAgentConfig(model_name="test-model", temperature=0, extra_params={})
        agent = ScaffoldingAgent(config)
        agent.prompt_builder_tool = mock_tools[0]
        agent.artifact_parser_tool = mock_tools[1]
        return agent

    def test_verify_redundancy_stops_flow(self, agent, mock_agents, mock_tools):
        reporter, vcs, researcher, reasoner, knowledge = mock_agents
        
        # Setup: Branch exists
        vcs.resolve_project_id.return_value = 1
        vcs.check_branch_exists.return_value = "http://existing-url"
        
        request = ScaffoldingOrder(
            issue_key="TEST-1",
            raw_instruction="instr",
            summary="summary",
            reporter="user",
            repository_url="http://repo"
        )
        
        # Act
        agent.execute_flow(request, reporter, vcs, researcher, reasoner, knowledge)
        
        # Assert
        reporter.report_start.assert_called_with("TEST-1")
        reporter.report_success.assert_called() # Should report redundancy as success (soft exit)
        reporter.transition_task.assert_called_with("TEST-1", TaskStatus.IN_REVIEW)
        
        # Verify subsequent steps NOT called
        researcher.investigate.assert_not_called()
        reasoner.reason.assert_not_called()
        vcs.create_branch.assert_not_called()

    def test_full_flow_success(self, agent, mock_agents, mock_tools):
        reporter, vcs, researcher, reasoner, knowledge = mock_agents
        prompt_tool, parser_tool = mock_tools
        
        # Setup: Branch does not exist
        vcs.resolve_project_id.return_value = 1
        vcs.check_branch_exists.return_value = None
        
        # Mock Generation
        researcher.investigate.return_value = "context"
        knowledge.retrieve_similar_solutions.return_value = "rag"
        prompt_tool.build_prompt.return_value = "prompt"
        reasoner.reason.return_value = "raw response"
        parser_tool.parse_response.return_value = [FileContentDTO("path", "content")]
        
        # Mock VCS Actions returning DTOs
        vcs.create_branch.return_value = BranchDTO("branch", "url")
        vcs.commit_files.return_value = CommitResultDTO("id", "url")
        vcs.create_merge_request.return_value = MergeRequestDTO("1", "http://mr-url")
        
        request = ScaffoldingOrder("TEST-1", "instr", "summary", "user", "http://repo", "stack")
        
        # Act
        agent.execute_flow(request, reporter, vcs, researcher, reasoner, knowledge)
        
        # Assert
        reporter.report_start.assert_called()
        prompt_tool.build_prompt.assert_called_with(request, ANY)
        reasoner.reason.assert_called_with("prompt", "test-model")
        vcs.create_branch.assert_called()
        vcs.commit_files.assert_called()
        vcs.create_merge_request.assert_called()
        
        reporter.report_success.assert_called_with("TEST-1", "MR Created: http://mr-url")
        reporter.transition_task.assert_called_with("TEST-1", TaskStatus.IN_REVIEW)

# --------------------------------------------------------------------------------
# Merged Tests from Refactoring
# --------------------------------------------------------------------------------
from software_factory_poc.application.ports.drivers.reporter import ReporterMessages

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

def test_scaffolding_agent_short_circuit_on_existing_branch():
    # Setup
    config = MagicMock(spec=ScaffoldingAgentConfig)
    config.project_allowlist = ["group"]
    config.model_name = "gpt-4"
    config.default_target_branch = "main"
    
    agent = ScaffoldingAgent(config)
    
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
