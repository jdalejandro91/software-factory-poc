
from unittest.mock import MagicMock, patch
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

def test_code_review_webhook_success(mock_settings):
    """
    Verifies:
    1. POST /api/v1/webhooks/jira/code-review-trigger returns 202.
    2. Payload is parsed correctly (Regex fixed).
    3. UseCase.execute is called with the correct Task configuration.
    """
    # 1. Setup Mock UseCase
    mock_use_case = MagicMock()
    
    # 2. Override Dependency
    from software_factory_poc.infrastructure.entrypoints.api.code_review_router import get_code_review_usecase
    app.dependency_overrides[get_code_review_usecase] = lambda: mock_use_case
    
    # 3. Define Payload
    import textwrap
    description = textwrap.dedent("""
    Requesting code review.
    ```yaml
    version: '1.0'
    code_review_params:
      gitlab_project_id: '123'
      source_branch_name: 'feature/abc'
    ```
    """).strip()

    payload = {
        "issue": {
            "key": "CR-TEST-1",
            "fields": {
                "summary": "Integration Test Review",
                "description": description
            }
        },
        "user": {
            "name": "tester",
            "displayName": "Tester"
        }
    }

    try:
        # 4. Execute Request
        headers = {"X-API-KEY": "test-secret"}
        response = client.post(
            "/api/v1/webhooks/jira/code-review-trigger", 
            json=payload, 
            headers=headers
        )
        
        # 5. Assert Response
        assert response.status_code == 202
        assert response.json()["message"] == "Code Review request queued."
        
        # 6. Assert Use Case Invocation
        assert mock_use_case.execute.called, "UseCase.execute should have been called"
        
        # Capture the Task argument passed to execute(task)
        call_args = mock_use_case.execute.call_args
        task_arg = call_args[0][0]
        
        # 7. Assert Configuration Extraction
        # The 'gitlab_project_id' should be strings or ints depending on YAML parsing. 
        # YAML '123' is usually string "123" unless implicit int. 
        # Safe comparison to '123' or 123 via str().
        
        config = task_arg.description.config
        code_review_params = config.get("code_review_params", {})
        
        assert str(code_review_params["gitlab_project_id"]) == "123"
        assert code_review_params["source_branch_name"] == "feature/abc"

    finally:
        # Clean up overrides
        app.dependency_overrides = {}
