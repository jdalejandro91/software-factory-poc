import pytest
from unittest.mock import MagicMock

from software_factory_poc.policy.poc_policy_service import PocPolicyService, PolicyViolationError
from software_factory_poc.config.settings_pydantic import Settings
from software_factory_poc.contracts.scaffolding_contract_model import ScaffoldingContractModel, GitLabTargetModel
from software_factory_poc.templates.template_manifest_model import TemplateManifestModel

@pytest.fixture
def mock_settings():
    settings = MagicMock(spec=Settings)
    settings.allowlisted_template_ids = ["allowed_tmpl"]
    settings.allowlisted_gitlab_project_ids = [123]
    settings.protected_branches = ["main", "master"]
    return settings

@pytest.fixture
def policy_service(mock_settings):
    return PocPolicyService(mock_settings)

@pytest.fixture
def valid_contract():
    return ScaffoldingContractModel(
        contract_version="1",
        template_id="allowed_tmpl",
        service_slug="test-service",
        gitlab=GitLabTargetModel(project_id=123)
    )

@pytest.fixture
def valid_manifest():
    return TemplateManifestModel(
        template_version="1",
        description="Test",
        expected_paths=["TEST"]
    )

def test_validate_success(policy_service, valid_contract, valid_manifest):
    policy_service.validate_request(valid_contract, valid_manifest, "feature/test")

def test_validate_template_violation(policy_service, valid_contract, valid_manifest):
    valid_contract.template_id = "forbidden_tmpl"
    with pytest.raises(PolicyViolationError) as exc:
        policy_service.validate_request(valid_contract, valid_manifest, "feature/test")
    assert "Template 'forbidden_tmpl' is not in the allowlist" in str(exc.value)

def test_validate_project_violation(policy_service, valid_contract, valid_manifest):
    valid_contract.gitlab.project_id = 999
    with pytest.raises(PolicyViolationError) as exc:
        policy_service.validate_request(valid_contract, valid_manifest, "feature/test")
    assert "GitLab Project ID '999' is not in the allowlist" in str(exc.value)

def test_validate_branch_violation(policy_service, valid_contract, valid_manifest):
    with pytest.raises(PolicyViolationError) as exc:
        policy_service.validate_request(valid_contract, valid_manifest, "main")
    assert "conflicts with a protected branch" in str(exc.value)
