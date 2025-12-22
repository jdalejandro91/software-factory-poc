import pytest
from pydantic import ValidationError
from software_factory_poc.contracts.scaffolding_contract_model import (
    ScaffoldingContractModel,
    GitLabTargetModel,
)

def test_contract_validation_happy_path():
    model = ScaffoldingContractModel(
        contract_version="1",
        template_id="t1",
        service_slug="s1",
        gitlab=GitLabTargetModel(project_id=1),
    )
    assert model.template_id == "t1"

def test_contract_validation_bad_version():
    with pytest.raises(ValidationError) as exc:
        ScaffoldingContractModel(
            contract_version="2",
            template_id="t1",
            service_slug="s1",
            gitlab=GitLabTargetModel(project_id=1),
        )
    assert "contract_version" in str(exc.value)

def test_contract_validation_empty_fields():
    with pytest.raises(ValidationError) as exc:
        ScaffoldingContractModel(
            contract_version="1",
            template_id="",
            service_slug="",
            gitlab=GitLabTargetModel(project_id=1),
        )
    assert "template_id" in str(exc.value)

def test_contract_validation_bad_project_id():
    with pytest.raises(ValidationError) as exc:
        ScaffoldingContractModel(
            contract_version="1",
            template_id="t1",
            service_slug="s1",
            gitlab=GitLabTargetModel(project_id=0),
        )
    assert "project_id" in str(exc.value)
