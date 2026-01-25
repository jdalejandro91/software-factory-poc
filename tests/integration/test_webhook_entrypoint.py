
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from software_factory_poc.main import app
from software_factory_poc.infrastructure.entrypoints.api.dtos.jira_webhook_dto import JiraWebhookDTO

client = TestClient(app)

@pytest.fixture
def mock_settings():
    with patch("software_factory_poc.infrastructure.entrypoints.api.security.Settings") as MockSettings:
        settings = MagicMock()
        settings.jira_webhook_secret.get_secret_value.return_value = "test-secret"
        MockSettings.return_value = settings
        yield settings

@pytest.fixture
def valid_jira_payload():
    return {
        "issue": {
            "key": "KAN-1",
            "fields": {
                "summary": "Scaffold App",
                "description": "gitlab_project_path: 'mock/project'\ninstruction: build app"
            }
        },
        "user": {
            "displayName": "Test User",
            "emailAddress": "test@example.com"
        }
    }

def test_jira_webhook_entrypoint_success(valid_jira_payload, mock_settings):
    # Mocking the usecase execution to avoid full system run
    with patch("software_factory_poc.infrastructure.entrypoints.api.jira_trigger_router.CreateScaffoldingUseCase") as MockUseCase, \
         patch("software_factory_poc.infrastructure.entrypoints.api.jira_trigger_router.AppConfig") as MockAppConfig, \
         patch("software_factory_poc.infrastructure.entrypoints.api.jira_trigger_router.ProviderResolver") as MockResolver:
        
        mock_instance = MockUseCase.return_value

        
        headers = {"X-API-KEY": "test-secret"}
        response = client.post("/api/v1/jira-webhook", json=valid_jira_payload, headers=headers)
        
        assert response.status_code == 202
        assert response.json()["issue_key"] == "KAN-1"
        
        # Verify provider resolver and usecase were involved (indirectly via router logic)
        # Background tasks are hard to test with TestClient without extra setup, 
        # but 202 implies it reached the "accepted" block.

def test_jira_webhook_invalid_secret(valid_jira_payload, mock_settings):
    headers = {"X-API-KEY": "wrong-secret"}
    response = client.post("/api/v1/jira-webhook", json=valid_jira_payload, headers=headers)
    assert response.status_code == 403

def test_jira_webhook_malformed_payload(mock_settings):
    # Patch AppConfig to prevent validation error during instantiation
    with patch("software_factory_poc.infrastructure.entrypoints.api.jira_trigger_router.AppConfig"):
        headers = {"X-API-KEY": "test-secret"}
        # Missing issue key
        payload = {"issue": {}} 
        response = client.post("/api/v1/jira-webhook", json=payload, headers=headers)
    
        # Validation error should be caught and returned as 200 (Ignored) per Jira requirement
        # Wait, Pydantic validation error raises RequestValidationError which returns 422 by default
        # UNLESS we have a try/except in the router or a custom handler.
        # The router manually validates with JiraWebhookDTO.model_validate_json inside try/except block.
        # So it should return 200 OK with status: ignored/error.
        
        assert response.status_code == 200
        assert response.json()["status"] in ["ignored", "error"]
