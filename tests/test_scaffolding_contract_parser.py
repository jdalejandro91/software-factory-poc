import pytest

from software_factory_poc.application.core.domain.exceptions.contract_parse_error import (
    ContractParseError,
)
from software_factory_poc.application.core.domain.services.helpers.text_block_extractor import (
    BLOCK_END,
    BLOCK_START,
)
from software_factory_poc.application.core.domain.services.scaffolding_contract_parser_service import (
    ScaffoldingContractParserService,
)


def test_parse_valid_contract():
    parser = ScaffoldingContractParserService()
    text = f"""
Title
{BLOCK_START}
version: "1"
technology_stack: "corp_nodejs_api"
target:
  project_id: 10
parameters:
  service_name: "My Service"
{BLOCK_END}
Footer
"""
    contract = parser.parse(text)
    assert contract.contract_version == "1"
    assert contract.technology_stack == "corp_nodejs_api"
    # Service slug derived from parameters service_name
    assert contract.service_slug == "My Service"
    assert contract.gitlab.project_id == 10

def test_parse_missing_block():
    parser = ScaffoldingContractParserService()
    with pytest.raises(ContractParseError) as exc:
        parser.parse("No contract here")
    assert "Could not find contract block" in str(exc.value)

def test_parse_invalid_yaml():
    parser = ScaffoldingContractParserService()
    text = f"{BLOCK_START}\n: invalid\n{BLOCK_END}"
    with pytest.raises(ContractParseError) as exc:
        parser.parse(text)
        assert "Could not find contract block" in str(exc.value)
