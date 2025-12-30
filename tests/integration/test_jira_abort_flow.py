import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from software_factory_poc.main import app
from software_factory_poc.infrastructure.entrypoints.api.jira_trigger_router import get_usecase, get_settings
from software_factory_poc.application.usecases.scaffolding.process_jira_request_usecase import ProcessJiraRequestUseCase
from software_factory_poc.application.core.entities.scaffolding_agent import ScaffoldingAgent
from software_factory_poc.infrastructure.providers.knowledge.confluence_mock_adapter import ConfluenceMockAdapter
from software_factory_poc.application.core.interfaces.llm_gateway import LLMGatewayPort
from software_factory_poc.configuration.main_settings import Settings
from software_factory_poc.application.ports.tools.jira_provider import JiraProvider
from software_factory_poc.application.ports.tools.gitlab_provider import GitLabProvider
from software_factory_poc.configuration.tools.tool_settings import ToolSettings

class MockLLMGateway(LLMGatewayPort):
    def __init__(self):
        self.call_count = 0

    def generate_code(self, prompt: str, model: str) -> str:
        self.call_count += 1
        return '{}'

mock_llm = MockLLMGateway()

# Using a separate Mock for this test to control branch_exists
mock_gitlab_abort = MagicMock(spec=GitLabProvider)
mock_jira_abort = MagicMock(spec=JiraProvider)

@pytest.fixture(autouse=True)
def setup_abort_overrides():

    def get_settings_override():
        s = Settings()
        from pydantic import SecretStr
        s.jira_webhook_secret = SecretStr("test-secret")
        return s

    def override_get_usecase_fn():
        kb_adapter = ConfluenceMockAdapter()
        agent = ScaffoldingAgent(llm_gateway=mock_llm, knowledge_port=kb_adapter)
        
        # Configure Mocks
        mock_gitlab_abort.resolve_project_id.return_value = 123
        mock_gitlab_abort.branch_exists.return_value = True # <--- CRITICAL: Branch exists
        
        # We need ToolSettings. Assuming Settings inherits or we can instantiate ToolSettings
        # Based on previous test, it passed Settings() to settings arg. 
        # But ProcessJiraRequestUseCase expects 'settings: ToolSettings'. 
        # Safe to use ToolSettings() if independent, or Settings().
        tool_settings = ToolSettings() 
        
        return ProcessJiraRequestUseCase(
            agent=agent, 
            jira_provider=mock_jira_abort, 
            gitlab_provider=mock_gitlab_abort, 
            settings=tool_settings
        )

    app.dependency_overrides[get_settings] = get_settings_override
    app.dependency_overrides[get_usecase] = override_get_usecase_fn
    yield
    app.dependency_overrides = {}

client = TestClient(app)

def test_jira_abort_when_branch_exists():
    mock_llm.call_count = 0 # Reset
    
    payload = {
        "webhookEvent": "jira:issue_created",
        "timestamp": 123456789,
        "issue": {
            "key": "KAN-999",
            "fields": {
                "summary": "Duplicate Feature",
                "description": """
```scaffolding
version: '1.0'
technology_stack: python
target:
  gitlab_project_path: 'group/duplicate'
parameters:
  service_name: 'dup-service'
```
""",
                "project": {"key": "KAN", "name": "Project"}
            }
        },
        "changelog": {
            "id": "1111",
            "items": [
                {
                    "field": "status",
                    "fieldtype": "jira",
                    "fromString": "Por hacer",
                    "toString": "En curso"
                }
            ]
        }
    }
    
    headers = {"X-API-Key": "test-secret"}
    response = client.post("/api/v1/jira-webhook", json=payload, headers=headers)
    
    assert response.status_code == 202
    
    # Verify Abort Logic
    
    # 1. Branch Existence Checked
    mock_gitlab_abort.branch_exists.assert_called_with(123, "feature/KAN-999-scaffolding")
    
    # 2. Jira Comment added about abort
    # Check if any call to add_comment contains "Rama Existente Detectada"
    calls = mock_jira_abort.add_comment.call_args_list
    assert any("Rama Existente Detectada" in str(c) for c in calls)
    
    # 3. Transitioned to "In Review" (STATE_SUCCESS)
    # Default ToolSettings: success="In Review"
    mock_jira_abort.transition_issue.assert_called_with("KAN-999", "In Review")
    
    # 4. Agent NOT called
    assert mock_llm.call_count == 0
    
    # 5. Create Branch and Merge Request NOT called
    mock_gitlab_abort.create_branch.assert_not_called()
    mock_gitlab_abort.create_merge_request.assert_not_called()
