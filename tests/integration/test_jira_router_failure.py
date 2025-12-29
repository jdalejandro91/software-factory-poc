import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from software_factory_poc.main import app
from software_factory_poc.infrastructure.entrypoints.api.jira_trigger_router import get_usecase
from software_factory_poc.application.usecases.scaffolding.process_jira_request_usecase import ProcessJiraRequestUseCase
from software_factory_poc.configuration.main_settings import Settings

client = TestClient(app)

def override_get_usecase_failure():
    # Mock UseCase that raises an exception
    mock_usecase = MagicMock(spec=ProcessJiraRequestUseCase)
    mock_usecase.execute.side_effect = Exception("System Failure Simulation")
    return mock_usecase

def test_jira_router_returns_json_error():
    # Arrange
    app.dependency_overrides[get_usecase] = override_get_usecase_failure
    
    payload = {
        "webhookEvent": "jira:issue_created",
        "timestamp": 123456789,
        "user": {"name": "tester", "displayName": "Integration Tester", "active": True},
        "issue": {
            "id": "1001",
            "key": "KAN-FAIL",
            "fields": {
                "summary": "Fail Test",
                "description": "Fail please",
                "project": {"key": "KAN"}
            }
        }
    }
    
    settings = Settings()
    headers = {"X-API-Key": settings.jira_webhook_secret.get_secret_value()}

    # Act
    try:
        response = client.post("/api/v1/jira-webhook", json=payload, headers=headers)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "error"
        assert data["message"] == "Scaffolding execution failed"
        assert data["error_type"] == "Exception"
        assert data["detail"] == "System Failure Simulation"
        assert data["issue_key"] == "KAN-FAIL"
        
    finally:
        # Cleanup overrides
        app.dependency_overrides = {}
