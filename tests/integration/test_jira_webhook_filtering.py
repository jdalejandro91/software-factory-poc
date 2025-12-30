import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from software_factory_poc.main import app
from software_factory_poc.infrastructure.entrypoints.api.jira_trigger_router import get_usecase, get_settings
from software_factory_poc.application.usecases.scaffolding.process_jira_request_usecase import ProcessJiraRequestUseCase
from software_factory_poc.configuration.main_settings import Settings
from pydantic import SecretStr

# Mock Usecase to verify calls
mock_usecase = MagicMock(spec=ProcessJiraRequestUseCase)

@pytest.fixture(autouse=True)
def setup_filtering_overrides():
    def get_settings_override():
        s = Settings()
        s.jira_webhook_secret = SecretStr("test-secret")
        # s.workflow_state_processing = "En curso"  <-- Removed
        return s

    def override_get_usecase_fn():
        return mock_usecase

    app.dependency_overrides[get_settings] = get_settings_override
    app.dependency_overrides[get_usecase] = override_get_usecase_fn
    yield
    app.dependency_overrides = {}

client = TestClient(app)

def test_jira_webhook_ignored_if_no_transition_to_processing():
    mock_usecase.execute.reset_mock()
    
    payload = {
        "webhookEvent": "jira:issue_updated",
        "timestamp": 123456789,
        "issue": {
            "key": "KAN-100",
            "fields": {
                "summary": "Ignored Update",
                "project": {"key": "KAN", "name": "Project"}
            }
        },
        "changelog": {
            "id": "100",
            "items": [
                {
                    "field": "description", # <--- Not status
                    "fromString": "Old",
                    "toString": "New"
                }
            ]
        }
    }
    
    headers = {"X-API-Key": "test-secret"}
    response = client.post("/api/v1/jira-webhook", json=payload, headers=headers)
    
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "accepted"
    assert "Request queued" in data["message"]
    
    # Usecase SHOULD be called now (Confianza ciega)
    mock_usecase.execute.assert_called_once()

def test_jira_webhook_accepted_if_transition_to_processing():
    mock_usecase.execute.reset_mock()
    
    payload = {
        "webhookEvent": "jira:issue_updated",
        "timestamp": 123456789,
        "issue": {
            "key": "KAN-101",
            "fields": {
                "summary": "Start Work",
                "project": {"key": "KAN", "name": "Project"}
            }
        },
        "changelog": {
            "id": "101",
            "items": [
                {
                    "field": "status", 
                    "fromString": "Por hacer",
                    "toString": "En curso" # <--- Setup override matches this
                }
            ]
        }
    }
    
    headers = {"X-API-Key": "test-secret"}
    response = client.post("/api/v1/jira-webhook", json=payload, headers=headers)
    
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "accepted"
    
    # Needs a small wait for BackgroundTasks? 
    # TestClient usually runs background tasks unless explicitly prevented? 
    # Actually, mocked usecase might not run immediately if async, but it's a sync call in router.
    # The routers `background_tasks.add_task` will execute after the response? 
    # FastAPI TestClient DOES execute background tasks.
    
    # mock_usecase.execute IS called.
    # Wait, add_task(usecase.execute, request)
    # verify call
    mock_usecase.execute.assert_called_once()

def test_jira_webhook_accepted_case_insensitive():
    mock_usecase.execute.reset_mock()
    
    payload = {
        "webhookEvent": "jira:issue_updated",
        "timestamp": 123456789,
        "issue": {
            "key": "KAN-102",
            "fields": {
                "summary": "Case Insensitive Test",
                "project": {"key": "KAN", "name": "Project"}
            }
        },
        "changelog": {
            "id": "102",
            "items": [
                {
                    "field": "status", 
                    "fromString": "Por hacer",
                    "toString": "en curso " # <--- Mixed case / whitespace
                }
            ]
        }
    }
    
    headers = {"X-API-Key": "test-secret"}
    response = client.post("/api/v1/jira-webhook", json=payload, headers=headers)
    
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "accepted"
    mock_usecase.execute.assert_called_once()
