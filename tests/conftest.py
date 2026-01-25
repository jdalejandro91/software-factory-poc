import os
import shutil
import tempfile
from pathlib import Path

import pytest
from unittest.mock import MagicMock
from software_factory_poc.application.core.agents.reporter.dtos.tracker_dtos import TaskDTO
from software_factory_poc.application.core.agents.vcs.dtos.vcs_dtos import MergeRequestDTO, BranchDTO, CommitResultDTO
from software_factory_poc.application.core.agents.common.dtos.file_content_dto import FileContentDTO
from software_factory_poc.application.core.agents.scaffolding.value_objects.scaffolding_order import ScaffoldingOrder

@pytest.fixture
def mock_task_dto_factory():
    def _create(id="KAN-1", title="Test Task", status="TO_DO"):
        return TaskDTO(id=id, title=title, status=status, description="Desc")
    return _create

@pytest.fixture
def mock_mr_dto_factory():
    def _create(id="1", web_url="http://gitlab/mr/1", state="opened"):
        return MergeRequestDTO(id=id, web_url=web_url, state=state)
    return _create

@pytest.fixture
def mock_scaffolding_order_factory():
    def _create(issue_key="TEST-123", summary="Summary", stack="python"):
        return ScaffoldingOrder(
            issue_key=issue_key,
            raw_instruction="Instr",
            summary=summary,
            reporter="User",
            repository_url="http://repo",
            technology_stack=stack
        )
    return _create

# from software_factory_poc.configuration.main_settings import Settings
from software_factory_poc.infrastructure.configuration.main_settings import Settings

# from software_factory_poc.configuration.tools.tool_settings import JiraAuthMode
from software_factory_poc.infrastructure.configuration.tool_settings import JiraAuthMode


@pytest.fixture
def temp_workspace():
    tmp = tempfile.mkdtemp()
    yield Path(tmp)
    shutil.rmtree(tmp)

@pytest.fixture
def settings(temp_workspace):
    return Settings(
        jira_base_url="https://jira.example.com",
        jira_api_token="mock_jira_token",
        jira_user_email="bot@example.com",
        jira_auth_mode=JiraAuthMode.CLOUD_API_TOKEN,
        gitlab_base_url="https://gitlab.example.com",
        gitlab_token="mock_gl_token",
        runtime_data_dir=temp_workspace / "runtime_data",
        template_catalog_root=temp_workspace / "templates",
        app_name="TestPoC",
        openai_api_key="mock_openai_key",
        confluence_base_url="https://confluence.example.com",
        confluence_user_email="mock@confluence.com",
        confluence_api_token="mock_confluence_token",
        jira_webhook_secret="mock_secret"
    )

@pytest.fixture
def populate_templates(settings):
    # Create the 'corp_nodejs_api' template in temp dir
    t_dir = settings.template_catalog_root / "corp_nodejs_api"
    os.makedirs(t_dir, exist_ok=True)
    
    (t_dir / "template_manifest.yaml").write_text("""
template_version: "1"
description: "Test Template"
expected_paths:
  - "README.md"
supported_vars:
  - "service_name"
""")
    (t_dir / "README.md.j2").write_text("# {{ service_name }}")
