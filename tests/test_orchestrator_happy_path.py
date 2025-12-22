import pytest
import respx
import os
from httpx import Response
from software_factory_poc.api.jira_trigger_router import get_orchestrator
from software_factory_poc.contracts.artifact_result_model import ArtifactRunStatusEnum
from software_factory_poc.contracts.scaffolding_contract_parser_service import BLOCK_START, BLOCK_END

@pytest.fixture
def full_orchestrator(settings):
    """Returns the full orchestrator graph using the test settings."""
    return get_orchestrator(settings)

@respx.mock
def test_orchestrator_happy_path(full_orchestrator, settings):
    # 1. Setup Template
    t_id = "corp_nodejs_api"
    t_dir = settings.template_catalog_root / t_id
    os.makedirs(t_dir, exist_ok=True)
    (t_dir / "template_manifest.yaml").write_text("""
template_version: "1"
description: "NodeJS API"
expected_paths: ["README.md"]
supported_vars: ["service_name"]
""")
    (t_dir / "README.md.j2").write_text("# {{ service_name }}")

    # 2. Mock Jira Get Issue
    issue_key = "PROJ-1"
    contract = f"""
{BLOCK_START}
contract_version: "1"
template_id: "{t_id}"
service_slug: "my-svc"
gitlab:
  project_id: 123
vars:
  service_name: "My Best Service"
{BLOCK_END}
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
    # Create Branch
    respx.post(f"{settings.gitlab_base_url}/api/v4/projects/123/repository/branches").mock(
        return_value=Response(201, json={"name": "scaffold/proj-1-my-svc"})
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
