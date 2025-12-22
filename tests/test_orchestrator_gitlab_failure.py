import pytest
import respx
import os
from httpx import Response
from software_factory_poc.api.jira_trigger_router import get_orchestrator
from software_factory_poc.contracts.artifact_result_model import ArtifactRunStatusEnum
from software_factory_poc.contracts.scaffolding_contract_parser_service import BLOCK_START, BLOCK_END

@respx.mock
def test_orchestrator_gitlab_failure(settings):
    # Allow the test template
    settings.allowlisted_template_ids.append("fail_test")
    orchestrator = get_orchestrator(settings)
    
    # Setup template
    t_id = "fail_test"
    t_dir = settings.template_catalog_root / t_id
    os.makedirs(t_dir, exist_ok=True)
    (t_dir / "template_manifest.yaml").write_text("""
template_version: "1"
description: "Fail Test"
expected_paths: ["README.md"]
""")
    (t_dir / "README.md.j2").write_text("content")

    issue_key = "PROJ-3"
    contract = f"""
{BLOCK_START}
contract_version: "1"
template_id: "{t_id}"
service_slug: "my-svc"
gitlab:
  project_id: 123
{BLOCK_END}
"""

    # Mock Jira
    respx.get(f"{settings.jira_base_url}/rest/api/3/issue/{issue_key}").mock(
        return_value=Response(200, json={
            "key": issue_key, "fields": {"summary": "S", "description": contract}
        })
    )
    
    # Mock GitLab Branch -> OK
    respx.post(f"{settings.gitlab_base_url}/api/v4/projects/123/repository/branches").mock(
        return_value=Response(201, json={"name": "branch"})
    )
    
    # Mock GitLab Commit -> FAIL 500
    respx.post(f"{settings.gitlab_base_url}/api/v4/projects/123/repository/commits").mock(
        return_value=Response(500, json={"message": "GitLab exploded"})
    )

    # Mock Jira Comment -> Reporting Failure
    jira_comment_mock = respx.post(f"{settings.jira_base_url}/rest/api/3/issue/{issue_key}/comment").mock(
        return_value=Response(201, json={"id": "comment_fail"})
    )

    # EXECUTE
    result = orchestrator.execute(issue_key)

    # VERIFY
    assert result.status == ArtifactRunStatusEnum.FAILED
    assert result.mr_url is None
    
    # Assert comment posted with system error
    assert jira_comment_mock.called
    payload = jira_comment_mock.calls.last.request.read()
    assert b"SCAFFOLDING FAILED (System Error)" in payload
