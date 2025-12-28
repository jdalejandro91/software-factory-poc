
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
mock_llm.generate_code.return_value = "Generated Code by Mock LLM"

def override_get_usecase():
    agent = ScaffoldingAgent(supported_models=["test-model"])
    kb = ConfluenceMockAdapter()
    return ProcessJiraRequestUseCase(agent, kb, mock_llm)

app.dependency_overrides[get_usecase] = override_get_usecase

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
                "description": "Please scaffolding this:\n```scaffolding\ninstruction: 'Create Clean Arch Shopping Cart'\n```"
            }
        }
    }
    
    # API Key
    headers = {"X-API-Key": Settings().jira_webhook_secret.get_secret_value()}
    
    response = client.post("/api/v1/jira-webhook", json=payload, headers=headers)
    
    # Verify Response
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "COMPLETED"
    assert data["issue_key"] == "KAN-1"
    
    # Verify LLM was called
    mock_llm.generate_code.assert_called_once()
    
    # Verify Prompt contained Architecture Guidelines from Confluence Mock
    args = mock_llm.generate_code.call_args
    prompt = args[0][0]
    
    assert "Fuentes base: Clean Architecture" in prompt
    assert "C4 mínimo" in prompt
    assert "USER REQUEST:\ninstruction: 'Create Clean Arch Shopping Cart'" in prompt

