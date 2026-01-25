import sys
import os
from unittest.mock import MagicMock

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from software_factory_poc.application.core.domain.agents.scaffolding.scaffolding_agent import ScaffoldingAgent
from software_factory_poc.application.core.domain.agents.scaffolding.scaffolding_order import ScaffoldingOrder
from software_factory_poc.application.core.domain.agents.scaffolding.scaffolding_agent_config import ScaffoldingAgentConfig
from software_factory_poc.application.core.domain.agents.vcs.vcs_agent import VcsAgent
from software_factory_poc.application.core.domain.agents.reasoner.reasoner_agent import ReasonerAgent
from software_factory_poc.application.core.domain.agents.reporter.reporter_agent import ReporterAgent
from software_factory_poc.application.core.domain.configuration.task_status import TaskStatus

# Mock TaskStatus if import fails (it shouldn't, but just in case of environment issues in test script)
# Actually let's assume it imports fine.

from software_factory_poc.application.core.ports.gateways.dtos import MergeRequestDTO, BranchDTO, CommitResultDTO

def test_flow():
    print("Testing ScaffoldingAgent 12-Line Refactor Flow...")
    
    # Mocks
    mock_tracker_gateway = MagicMock()
    mock_vcs_gateway = MagicMock()
    mock_researcher = MagicMock()
    mock_knowledge = MagicMock()
    mock_llm_gateway = MagicMock()
    
    # Setup Mocks
    mock_vcs_gateway.resolve_project_id.return_value = 101
    mock_vcs_gateway.branch_exists.return_value = False
    
    # Mock DTO returns
    mock_vcs_gateway.create_merge_request.return_value = MergeRequestDTO(id="1", web_url="http://gitlab/mr/1")
    mock_vcs_gateway.create_branch.return_value = BranchDTO(name="feature/TEST-123/scaffolding", web_url="http://gitlab/branch")
    mock_vcs_gateway.commit_files.return_value = CommitResultDTO(id="sha123", web_url="http://gitlab/commit/sha123")
    
    mock_researcher.investigate.return_value = "Research done."
    mock_knowledge.retrieve_similar_solutions.return_value = "Knowledge found."
    
    mock_llm_gateway.generate_code.return_value = """
<<<FILE:README.md>>>
# Test
<<<END>>>
"""

    # Instantiate Agents
    # Note: verify_refactor failure was due to missing args. Passing them now.
    vcs_agent = VcsAgent(name="Vcs", role="Vcs", goal="Vcs", gateway=mock_vcs_gateway)
    reasoner_agent = ReasonerAgent(name="Reasoner", role="Reasoner", goal="Reason", llm_gateway=mock_llm_gateway)
    reporter_agent = ReporterAgent(name="Reporter", role="Reporter", goal="Report", gateway=mock_tracker_gateway)
    
    config = ScaffoldingAgentConfig(model_name="gpt-test", temperature=0, extra_params={})
    orchestrator = ScaffoldingAgent(config=config)
    
    request = ScaffoldingOrder(
        issue_key="TEST-123",
        raw_instruction="Instruction",
        summary="Summary",
        reporter="User",
        repository_url="http://gitlab/repo.git"
    )

    # Execute
    orchestrator.execute_flow(
        request=request,
        reporter=reporter_agent,
        vcs=vcs_agent,
        researcher=mock_researcher,
        reasoner=reasoner_agent,
        knowledge=mock_knowledge
    )

    # Verify atomic calls
    print("Verifying interactions...")
    
    # Reporter
    reporter_agent.gateway.add_comment.assert_any_call("TEST-123", "🤖 Iniciando tarea de scaffolding...")
    
    # VCS
    mock_vcs_gateway.branch_exists.assert_called() # Inside check_branch_exists
    
    # Reasoner
    mock_llm_gateway.generate_code.assert_called()
    call_args = mock_llm_gateway.generate_code.call_args
    assert call_args.kwargs['model'] == "gpt-test"
    
    # VCS Publish
    mock_vcs_gateway.create_branch.assert_called()
    mock_vcs_gateway.commit_files.assert_called()
    mock_vcs_gateway.create_merge_request.assert_called()
    
    # Reporter Success
    reporter_agent.gateway.add_comment.assert_any_call("TEST-123", "✅ Éxito: MR Created: http://gitlab/mr/1")
    reporter_agent.gateway.transition_status.assert_called() 
    
    print("SUCCESS: Flow executed correctly.")

if __name__ == "__main__":
    test_flow()
