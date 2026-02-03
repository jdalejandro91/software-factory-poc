
from unittest.mock import MagicMock, patch, ANY
import pytest
from fastapi.testclient import TestClient
from software_factory_poc.main import app

client = TestClient(app)

@pytest.fixture
def mock_settings():
    with patch("software_factory_poc.infrastructure.entrypoints.api.security.Settings") as MockSettings:
        settings = MagicMock()
        settings.jira_webhook_secret.get_secret_value.return_value = "test-secret"
        MockSettings.return_value = settings
        yield settings

@pytest.fixture
def valid_jira_payload_with_code_block():
    description_with_yaml = """
    Please review this code.
    
    ```yaml
    code_review_params:
      gitlab_project_id: 101
      source_branch_name: feature/auth-refactor
      review_request_url: https://gitlab.com/group/project/-/merge_requests/42
    ```
    """
    return {
        "issue": {
            "key": "CR-123",
            "fields": {
                "summary": "Code Review Request",
                "description": description_with_yaml
            }
        },
        "user": {
            "name": "developer.one",
            "displayName": "Developer One"
        }
    }

def test_code_review_trigger_success_with_refactored_mapper(valid_jira_payload_with_code_block, mock_settings):
    """
    Verifies that the Code Review Trigger endpoint uses the Refactored Mapper
    to correctly extract 'code_review_params' from a ```yaml block.
    """
    # Create a mock UseCase
    mock_use_case = MagicMock()
    
    # Define override
    from software_factory_poc.infrastructure.entrypoints.api.code_review_router import get_code_review_usecase
    app.dependency_overrides[get_code_review_usecase] = lambda: mock_use_case
    
    try:
        # Execute Request
        headers = {"X-API-KEY": "test-secret"}
        response = client.post(
            "/api/v1/webhooks/jira/code-review-trigger", 
            json=valid_jira_payload_with_code_block, 
            headers=headers
        )
        
        # 1. Assert Response
        assert response.status_code == 202
        assert response.json()["message"] == "Code Review request queued."
        
        # 2. Verify Mapping Logic
        # We check the arguments passed to the UseCase.execute(task)
        # The router calls: background_tasks.add_task(usecase.execute, task_entity)
        
        assert mock_use_case.execute.called
        call_args = mock_use_case.execute.call_args
        task_arg = call_args[0][0]
        
        print(f"\n[DEBUG] Captured Task Config:\n{task_arg.description.config}")
        
        # Verify the Mapper parsed the nested YAML correctly
        params = task_arg.description.config.get("code_review_params", {})
        assert params.get("gitlab_project_id") == 101
        assert params.get("source_branch_name") == "feature/auth-refactor"
        assert params.get("review_request_url") == "https://gitlab.com/group/project/-/merge_requests/42"

    finally:
        # Clean up overrides
        app.dependency_overrides = {}
