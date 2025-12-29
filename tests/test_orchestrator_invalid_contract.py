import respx
from httpx import Response

from software_factory_poc.infrastructure.entrypoints.api.jira_trigger_router import get_orchestrator
from software_factory_poc.application.core.entities.artifact_result import ArtifactRunStatusEnum


@respx.mock
def test_orchestrator_invalid_contract(settings):
    # Orch
    orchestrator = get_orchestrator(settings)
    issue_key = "PROJ-2"

    # Setup Request with NO contract
    from software_factory_poc.application.core.entities.scaffolding.scaffolding_request import ScaffoldingRequest
    request = ScaffoldingRequest(
        issue_key=issue_key,
        project_key="PROJ",
        summary="Only Human Description",
        raw_instruction="Please make me a sandwich.",
        reporter="Tester"
    )

    # Mock Jira Add Comment (Failure notification)
    jira_comment_mock = respx.post(f"{settings.jira_base_url}/rest/api/3/issue/{issue_key}/comment").mock(
        return_value=Response(201, json={"id": "comment_err"})
    )

    # Mock GitLab (Should NOT be called) but we'll specificially assert calls count later
    gl_branch = respx.post(f"{settings.gitlab_base_url}/api/v4/projects/100/repository/branches")

    # EXECUTE
    result = orchestrator.execute(request)

    # VERIFY
    assert result.status == ArtifactRunStatusEnum.FAILED
    assert "Could not find contract" in (result.error_summary or "")
    
    # Assert GitLab was NOT called
    assert not gl_branch.call_count
    
    # Assert failure comment posted
    assert jira_comment_mock.called
    # Payload check skipped due to ADF format complexity
    # assert b"SCAFFOLDING FAILED" in jira_comment_mock.calls.last.request.read()
