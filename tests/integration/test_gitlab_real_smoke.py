import os
import uuid

import pytest

from software_factory_poc.config.settings_pydantic import Settings
from software_factory_poc.integrations.gitlab.gitlab_client import GitLabClient
from software_factory_poc.integrations.gitlab.gitlab_payload_builder_service import (
    GitLabPayloadBuilderService,
)


@pytest.mark.skipif(
    os.environ.get("RUN_REAL_GITLAB") != "1",
    reason="Skipping real GitLab integration test. Set RUN_REAL_GITLAB=1 to run."
)
def test_gitlab_real_smoke():
    """
    Smoke test against real GitLab API.
    Requires:
    - GITLAB_BASE_URL
    - GITLAB_TOKEN
    - A valid project path to resolve (defaults to 'gitlab-org/gitlab' just for resolution test if not provided)
    """
    settings = Settings() # Reads env vars
    
    # Validation
    if not settings.gitlab_token:
        pytest.fail("GITLAB_TOKEN not set in environment")

    client = GitLabClient(settings, GitLabPayloadBuilderService())

    # 1. Test Project ID Resolution
    # Use a public project for resolution test if user didn't specify a private one to test with
    # But ideally we use something safe. Let's try to resolve a well known public project 
    # OR expect a specific env var for target.
    # We will assume the user has a sandbox project or group.
    
    target_path = os.environ.get("GITLAB_TEST_PROJECT_PATH", "gitlab-org/gitlab")
    
    print(f"\nResolving ID for {target_path}...")
    try:
        project_id = client.resolve_project_id(target_path)
        print(f"Resolved {target_path} -> {project_id}")
        assert project_id > 0
    except Exception as e:
        pytest.fail(f"Failed to resolve project {target_path}: {e}")

    # 2. Test Branch Creation (Only if we have a writable project configured)
    # This part is risky for a generic smoke test on a public repo (403).
    # We will only proceed if GITLAB_TEST_WRITE_PROJECT_ID is set.
    write_layout_id = os.environ.get("GITLAB_TEST_WRITE_PROJECT_ID")
    if write_layout_id:
        pid = int(write_layout_id)
        branch_name = f"test-smoke-{uuid.uuid4()}"
        print(f"Creating branch {branch_name} in {pid}")
        try:
            client.create_branch(pid, branch_name, "main")
            print("Branch created.")
            
            # Helper to cleanup would be nice, but this is a rough smoke test.
        except Exception as e:
            pytest.fail(f"Failed write operation: {e}")
    else:
        print("Skipping write operations (GITLAB_TEST_WRITE_PROJECT_ID not set)")
