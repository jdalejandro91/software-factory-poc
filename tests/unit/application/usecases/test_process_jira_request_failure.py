import pytest
from unittest.mock import MagicMock
from software_factory_poc.application.usecases.scaffolding.process_jira_request_usecase import ProcessJiraRequestUseCase
from software_factory_poc.application.core.entities.scaffolding.scaffolding_request import ScaffoldingRequest
from software_factory_poc.application.core.entities.scaffolding_agent import ScaffoldingAgent
from software_factory_poc.application.ports.tools.jira_provider import JiraProvider
from software_factory_poc.application.ports.tools.gitlab_provider import GitLabProvider

def test_execute_handles_exception_and_attempts_rollback():
    # Arrange
    mock_agent = MagicMock(spec=ScaffoldingAgent)
    mock_jira = MagicMock(spec=JiraProvider)
    mock_gitlab = MagicMock(spec=GitLabProvider)
    
    usecase = ProcessJiraRequestUseCase(
        agent=mock_agent,
        jira_provider=mock_jira,
        gitlab_provider=mock_gitlab
    )
    
    request = ScaffoldingRequest(
        issue_key="TEST-123",
        project_key="TEST",
        summary="Test Summary",
        raw_instruction="Do something",
        reporter="Tester"
    )
    
    # Simulate Agent Failure
    target_exception = Exception("Model Overload")
    mock_agent.execute_mission.side_effect = target_exception
    
    # Act
    with pytest.raises(Exception) as exc_info:
        usecase.execute(request)
        
    # Assert
    assert str(exc_info.value) == "Model Overload"
    
    # Verify Jira interactions
    # 1. Start notification
    mock_jira.add_comment.assert_any_call("TEST-123", "🤖 Iniciando agente de scaffolding...")
    
    # 2. Error notification (Partial match check due to formatting)
    # We check if add_comment was called with a string containing specific phrases
    error_call_args = mock_jira.add_comment.call_args_list[-1] # Last call
    msg_content = error_call_args[0][1]
    
    assert "⚠️ <b>Interrupción del Scaffolding</b>" in msg_content
    assert "Model Overload" in msg_content
    assert "To Do" in msg_content
    
    # 3. Rollback transition
    mock_jira.transition_issue.assert_called_with("TEST-123", "To Do")
