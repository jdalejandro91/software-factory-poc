import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from software_factory_poc.main import app 
from software_factory_poc.infrastructure.configuration.main_settings import Settings

client = TestClient(app)

@pytest.fixture
def mock_settings():
    return Settings(jira_webhook_secret="test-secret-123")

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data

def test_webhook_missing_auth():
    response = client.post("/api/v1/jira-webhook", json={})
    assert response.status_code == 403 

def test_webhook_invalid_auth():
    response = client.post(
        "/api/v1/jira-webhook", 
        json={}, 
        headers={"X-API-KEY": "wrong-secret"}
    )
    assert response.status_code == 403

def test_webhook_valid_payload_success():
    # Helper to mock dependencies
    mock_uc_instance = MagicMock()
    
    # Override Auth and UseCase
    from software_factory_poc.infrastructure.entrypoints.api.security import validate_api_key
    from software_factory_poc.infrastructure.entrypoints.api.jira_trigger_router import get_usecase
    
    app.dependency_overrides[validate_api_key] = lambda: "secret"
    app.dependency_overrides[get_usecase] = lambda: mock_uc_instance

    payload = {
        "webhookEvent": "jira:issue_created",
        "issue": {
            "key": "KAN-3",
            "fields": {
                "summary": "Test Issue",
                "description": "Req.\n\n```scaffolding\nversion: \"1.0\"\nservice_slug: \"test-service\"\ntechnology_stack: \"Python\"\ntarget:\n  gitlab_project_path: \"group/project\"\n```"
            }
        },
        "user": {"displayName": "Tester"}
    }

    response = client.post(
        "/api/v1/jira-webhook",
        json=payload,
        headers={"X-API-KEY": "secret"}
    )

    app.dependency_overrides = {} # Cleanup

    assert response.status_code == 202
    assert response.json()["status"] == "accepted"
    
    # Verify UseCase execute was called
    # Since it's a BackgroundTask, we might need to verfy if it was added to the queue
    # Ideally we'd verify mock_uc_instance.execute.assert_called_once() 
    # But TestClient with BackgroundTasks runs them. 
    mock_uc_instance.execute.assert_called_once()
    
    # Verify UseCase was called (via BackgroundTasks - tricky in TestClient without explicit Block)
    # BackgroundTasks usually run after response. 
    # With TestClient, they run immediately? Let's check args
    
    # Note: mocking dependencies=[Depends] is hard with patch unless overridden in app.dependency_overrides
    # But here we patched the imported symbol in the router module.

def test_webhook_no_scaffolding_block_ignored():
    # Use dependency override for auth
    from software_factory_poc.infrastructure.entrypoints.api.security import validate_api_key
    app.dependency_overrides[validate_api_key] = lambda: "secret"

    payload = {
        "issue": {
            "key": "KAN-4",
            "fields": {
                "summary": "Just a normal issue",
                "description": "No scaffolding here."
            }
        },
        "user": {"displayName": "Tester"}
    }

    response = client.post("/api/v1/jira-webhook", json=payload)
    
    # Should be 200 OK (ignored)
    assert response.status_code == 200
    assert response.json()["status"] == "ignored"

    app.dependency_overrides = {}
