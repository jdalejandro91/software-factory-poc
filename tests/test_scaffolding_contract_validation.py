import pytest
from pydantic import ValidationError

from software_factory_poc.contracts.scaffolding_contract_model import (
    GitLabTargetModel,
    ScaffoldingContractModel,
)


def test_contract_validation_happy_path():
    model = ScaffoldingContractModel(
        version="1",
        template="t1",
        # service_slug is optional/computed
        target=GitLabTargetModel(project_id=1),
        parameters={"service_name": "s1"}
    )
    assert model.template_id == "t1"

def test_contract_validation_bad_version():
    with pytest.raises(ValidationError) as exc:
        ScaffoldingContractModel(
            version="2",
            template="t1",
            target=GitLabTargetModel(project_id=1),
        )
    assert "contract_version" in str(exc.value)

def test_contract_validation_empty_fields():
    with pytest.raises(ValidationError) as exc:
        ScaffoldingContractModel(
            version="1",
            template="",
            target=GitLabTargetModel(project_id=1),
        )
    assert "template_id" in str(exc.value)

def test_contract_validation_bad_project_id():
    with pytest.raises(ValidationError) as exc:
        ScaffoldingContractModel(
            version="1",
            template="t1",
            target=GitLabTargetModel(project_id=0),
        )
    assert "project_id" in str(exc.value)
