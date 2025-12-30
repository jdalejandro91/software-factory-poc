import pytest
from pydantic import ValidationError

from software_factory_poc.application.core.entities.scaffolding.scaffolding_contract import (
    GitLabTargetModel,
    ScaffoldingContractModel,
)


def test_contract_validation_happy_path():
    data = {
        "version": "1.0",
        "technology_stack": "node-express",
        "target": {"project_id": 123},
        "parameters": {"service_name": "demo"}
    }
    model = ScaffoldingContractModel(**data)
    assert model.technology_stack == "node-express"

def test_contract_validation_bad_version():
    with pytest.raises(ValidationError) as exc:
        ScaffoldingContractModel(
            version="2",
            technology_stack="t1",
            target=GitLabTargetModel(project_id=1),
        )
    assert "contract_version" in str(exc.value)

def test_contract_validation_empty_fields():
    with pytest.raises(ValidationError) as exc:
        ScaffoldingContractModel(
            version="1",
            technology_stack="",
            target=GitLabTargetModel(project_id=1),
        )
    assert "technology_stack" in str(exc.value)

def test_contract_validation_bad_project_id():
    with pytest.raises(ValidationError) as exc:
        ScaffoldingContractModel(
            version="1",
            technology_stack="t1",
            target=GitLabTargetModel(project_id=0),
        )
    assert "project_id" in str(exc.value)
