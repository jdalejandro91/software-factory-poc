import pytest
from unittest.mock import MagicMock, ANY
from software_factory_poc.application.core.agents.scaffolding.scaffolding_agent import ScaffoldingAgent
from software_factory_poc.application.core.agents.scaffolding.scaffolding_agent_config import ScaffoldingAgentConfig
from software_factory_poc.application.core.agents.scaffolding.scaffolding_order import ScaffoldingOrder
from software_factory_poc.application.core.ports.gateways.dtos import FileContentDTO, MergeRequestDTO, BranchDTO, CommitResultDTO
from software_factory_poc.application.core.domain.configuration.task_status import TaskStatus

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
