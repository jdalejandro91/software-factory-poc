from unittest.mock import AsyncMock

import pytest
import respx
from httpx import Response

from software_factory_poc.infrastructure.entrypoints.api.jira_trigger_router import get_orchestrator
from software_factory_poc.contracts.artifact_result_model import ArtifactRunStatusEnum
from software_factory_poc.contracts.scaffolding_contract_parser_service import (
    BLOCK_END,
    BLOCK_START,
)


@pytest.fixture
def full_orchestrator(settings):
    """Returns the full orchestrator graph using the test settings."""
    return get_orchestrator(settings)

@respx.mock
def test_orchestrator_happy_path(full_orchestrator, settings):
    # 1. Setup GenAI Mock
    full_orchestrator.genai_service.generate_scaffolding = AsyncMock(
        return_value={"README.md": "# GenAI Generated Service"}
    )

    # 2. Mock Jira Get Issue
    issue_key = "PROJ-1"
    contract = f"""
{BLOCK_START}
version: "1"
template: "any-template"
target:
  project_id: 123
parameters:
  service_name: "My Best Service"
{BLOCK_END}
Just some description that will be hashed.
"""
    
    respx.get(f"{settings.jira_base_url}/rest/api/3/issue/{issue_key}").mock(
        return_value=Response(200, json={
            "key": issue_key,
            "fields": {
                "summary": "Scaffold this",
                "description": contract
            }
        })
    )

    # 3. Mock GitLab Calls
    # Check Branch (GET) - 404 Not Found (New Branch)
    # branch_name = feature/proj-1-my-best-service-scaffold
    respx.get(f"{settings.gitlab_base_url}/api/v4/projects/123/repository/branches/feature%2Fproj-1-my-best-service-scaffold").mock(
        return_value=Response(404)
    )
    # Create Branch (POST)
    respx.post(f"{settings.gitlab_base_url}/api/v4/projects/123/repository/branches").mock(
        return_value=Response(201, json={"name": "feature/proj-1-my-best-service-scaffold", "web_url": "http://gitlab.com/branch"})
    )
    # Check File Existence (HEAD) - 404 (New File)
    respx.head(f"{settings.gitlab_base_url}/api/v4/projects/123/repository/files/README.md").mock(
        return_value=Response(404)
    )
    # Commit
    respx.post(f"{settings.gitlab_base_url}/api/v4/projects/123/repository/commits").mock(
        return_value=Response(201, json={"id": "commit_hash"})
    )
    # Create MR
    mock_mr_url = "https://gitlab.example.com/mr/1"
    respx.post(f"{settings.gitlab_base_url}/api/v4/projects/123/merge_requests").mock(
        return_value=Response(201, json={
            "id": 50,
            "iid": 1,
            "web_url": mock_mr_url
        })
    )

    # 4. Mock Jira Add Comment
    jira_comment_mock = respx.post(f"{settings.jira_base_url}/rest/api/3/issue/{issue_key}/comment").mock(
        return_value=Response(201, json={"id": "comment_123"})
    )

    # EXECUTE
    result = full_orchestrator.execute(issue_key)

    # VERIFY
    assert result.status == ArtifactRunStatusEnum.COMPLETED
    assert result.issue_key == issue_key
    assert result.mr_url == mock_mr_url
    
    # Verify Jira comment content contains success
    assert jira_comment_mock.called
    payload = jira_comment_mock.calls.last.request.read()
    assert b"Scaffolding Success" in payload
    assert mock_mr_url.encode() in payload
    
    # Verify GenAI was called
    full_orchestrator.genai_service.generate_scaffolding.assert_called_once()

