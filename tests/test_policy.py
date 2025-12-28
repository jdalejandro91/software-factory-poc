from unittest.mock import MagicMock

import pytest

from software_factory_poc.configuration.main_settings import Settings
from software_factory_poc.application.core.entities.scaffolding.scaffolding_contract import (
    GitLabTargetModel,
    ScaffoldingContractModel,
)
from software_factory_poc.policy.poc_policy_service import PocPolicyService, PolicyViolationError


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
        version="1",
        template="allowed_tmpl",
        target=GitLabTargetModel(project_id=123),
        parameters={"service_name": "test-service"}
    )

def test_validate_success(policy_service, valid_contract):
    policy_service.validate_request(valid_contract, "feature/test")

def test_validate_branch_violation(policy_service, valid_contract):
    with pytest.raises(PolicyViolationError) as exc:
        policy_service.validate_request(valid_contract, "main")
    assert "conflicts with a protected branch" in str(exc.value)
