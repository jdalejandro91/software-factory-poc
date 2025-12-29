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
    
    from software_factory_poc.configuration.tools.tool_settings import ToolSettings
    mock_settings = MagicMock(spec=ToolSettings)
    mock_settings.workflow_state_initial = "To Do"
    mock_settings.workflow_state_processing = "Processing"
    mock_settings.workflow_state_success = "Success"

    usecase = ProcessJiraRequestUseCase(
        agent=mock_agent,
        jira_provider=mock_jira,
        gitlab_provider=mock_gitlab,
        settings=mock_settings
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
    mock_jira.add_comment.assert_any_call("TEST-123", "🤖 Iniciando misión de scaffolding...")
    
    # 2. Error notification (ADF Panel Check)
    # We check if add_comment was called with a dict (ADF) containing specific error text
    error_call_args = mock_jira.add_comment.call_args_list[-1] # Last call
    msg_payload = error_call_args[0][1] # argument 1 is body
    
    assert isinstance(msg_payload, dict)
    assert msg_payload["type"] == "doc"
    # Drill down to find the text "Model Overload"
    # ADF structure is deep, so we just check string representation or key elements
    # But better to check structure reasonably
    
    panel = msg_payload["content"][0]
    assert panel["type"] == "panel"
    assert panel["attrs"]["panelType"] == "error"
    
    # Check if error detail is present in content
    # Converting to string to search is easier for test
    payload_str = str(msg_payload)
    assert "Model Overload" in payload_str
    assert "Misión Abortada" in payload_str
    
    # 3. Rollback transition
    mock_jira.transition_issue.assert_called_with("TEST-123", "To Do")
