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
        raw_instruction="```yaml\nversion: '1.0'\ntechnology_stack: 'python'\ntarget: { gitlab_project_path: 'foo/bar' }\nparameters: { service_name: 'test-service' }\n```",
        reporter="Tester"
    )
    
    # Simulate Agent Failure
    mock_gitlab.branch_exists.return_value = False
    target_exception = Exception("Model Overload")
    mock_agent.execute_mission.side_effect = target_exception
    
    # Act
    with pytest.raises(Exception) as exc_info:
        usecase.execute(request)
        
    # Assert
    assert str(exc_info.value) == "Model Overload"
    
    # Verify Jira interactions
    # 1. Start notification
    mock_jira.add_comment.assert_any_call("TEST-123", "🤖 Iniciando tarea de scaffolding...")
    
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
    assert "Exception: Model Overload" in payload_str
    assert "No se pudo completar la Tarea" in payload_str
    
    # 3. Rollback transition
    mock_jira.transition_issue.assert_called_with("TEST-123", "To Do")

def test_execute_handles_existing_branch():
    # Arrange
    mock_agent = MagicMock(spec=ScaffoldingAgent)
    mock_jira = MagicMock(spec=JiraProvider)
    mock_gitlab = MagicMock(spec=GitLabProvider)
    
    from software_factory_poc.configuration.tools.tool_settings import ToolSettings
    mock_settings = MagicMock(spec=ToolSettings)
    mock_settings.workflow_state_initial = "To Do"
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
        raw_instruction="```yaml\nversion: '1.0'\ntechnology_stack: 'python'\ntarget: { gitlab_project_path: 'foo/bar' }\nparameters: { service_name: 'test-service' }\n```",
        reporter="Tester"
    )

    # Simulate Branch Exists
    mock_gitlab.resolve_project_id.return_value = 101
    mock_gitlab.branch_exists.return_value = True

    # Act
    result = usecase.execute(request)

    # Assert
    assert result == "SKIPPED_BRANCH_EXISTS"
    
    # Verify Info Panel
    # Call args: [call('TEST-123', '🤖 ...'), call('TEST-123', {...})]
    assert mock_jira.add_comment.call_count == 2
    
    info_call = mock_jira.add_comment.call_args_list[-1]
    msg_payload = info_call[0][1]
    
    assert isinstance(msg_payload, dict)
    panel = msg_payload["content"][0]
    assert panel["type"] == "panel"
    assert panel["attrs"]["panelType"] == "info"
    
    payload_str = str(msg_payload)
    assert "Rama Existente Detectada" in payload_str
    
    # Agent NOT called
    mock_agent.execute_mission.assert_not_called()
    
    # Transition to Success
    mock_jira.transition_issue.assert_called_with("TEST-123", "Success")
