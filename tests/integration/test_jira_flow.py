
from unittest.mock import Mock
from fastapi.testclient import TestClient
import pytest

from software_factory_poc.main import app
from software_factory_poc.infrastructure.entrypoints.api.jira_trigger_router import get_usecase
from software_factory_poc.application.usecases.scaffolding.process_jira_request_usecase import ProcessJiraRequestUseCase
from software_factory_poc.application.core.entities.scaffolding_agent import ScaffoldingAgent
from software_factory_poc.infrastructure.providers.knowledge.confluence_mock_adapter import ConfluenceMockAdapter
from software_factory_poc.application.core.interfaces.llm_gateway import LLMGatewayPort
from software_factory_poc.configuration.main_settings import Settings

mock_llm = Mock(spec=LLMGatewayPort)
mock_llm.generate_code.return_value = '{"main.py": "print(\'Generated Code by Mock LLM\')"}'

@pytest.fixture(autouse=True)
def setup_overrides():
    from software_factory_poc.infrastructure.providers.knowledge.confluence_mock_adapter import ConfluenceMockAdapter
    from software_factory_poc.application.core.entities.scaffolding_agent import ScaffoldingAgent
    from software_factory_poc.application.ports.tools.jira_provider import JiraProvider
    from software_factory_poc.application.ports.tools.gitlab_provider import GitLabProvider
    from software_factory_poc.infrastructure.entrypoints.api.jira_trigger_router import get_settings
    
    def override_get_usecase():
        agent = ScaffoldingAgent(llm_gateway=mock_llm, knowledge_port=ConfluenceMockAdapter(), model_priority_list=["test-model"])
        kb = ConfluenceMockAdapter()
        return ProcessJiraRequestUseCase(
            agent=agent, 
            jira_provider=Mock(spec=JiraProvider), 
            gitlab_provider=Mock(spec=GitLabProvider), 
            settings=Settings()
        )

    def get_settings_override():
        s = Settings()
        from pydantic import SecretStr
        s.jira_webhook_secret = SecretStr("test-secret")
        return s

    app.dependency_overrides[get_usecase] = override_get_usecase
    app.dependency_overrides[get_settings] = get_settings_override
    yield
    app.dependency_overrides = {}

client = TestClient(app)

def test_jira_flow_integration():
    # Payload KAN-1
    payload = {
        "webhookEvent": "jira:issue_created",
        "timestamp": 12345678,
        "user": {
            "name": "tester",
            "displayName": "Integration Tester",
            "active": True
        },
        "issue": {
            "id": "1001",
            "key": "KAN-1",
            "fields": {
                "summary": "Shopping Cart MVP",
                "description": "Please scaffolding this:\n```scaffolding\nversion: '1'\ntechnology_stack: 'python-api'\ntarget:\n  project_id: 123\nparameters:\n  service_name: 'shopping-cart'\n```",
                "project": {
                    "key": "KAN",
                    "name": "Kanban Project"
                }
            }
        }
    }
    
    # API Key
    headers = {"X-API-Key": "test-secret"}
    
    response = client.post("/api/v1/jira-webhook", json=payload, headers=headers)
    
    # Verify Response
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "accepted"
    assert data["issue_key"] == "KAN-1"
    
    # Verify LLM was called
    mock_llm.generate_code.assert_called_once()
    
    # Verify Prompt contained Architecture Guidelines from Confluence Mock
    args = mock_llm.generate_code.call_args
    prompt = args[0][0]
    
    assert "Shopping Cart Architecture (Modular Monolith)" in prompt
    assert "USER REQUEST (Contains 'technology_stack'" in prompt

