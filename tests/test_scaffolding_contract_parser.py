import pytest
from software_factory_poc.contracts.scaffolding_contract_parser_service import (
    ScaffoldingContractParserService,
    ContractParseError,
    BLOCK_START,
    BLOCK_END,
)

def test_parse_valid_contract():
    parser = ScaffoldingContractParserService()
    text = f"""
Title
{BLOCK_START}
contract_version: "1"
template_id: "corp_nodejs_api"
service_slug: "my-svc"
gitlab:
    project_id: 10
vars:
    service_name: "My Service"
{BLOCK_END}
Footer
"""
    contract = parser.parse(text)
    assert contract.template_id == "corp_nodejs_api"
    assert contract.service_slug == "my-svc"
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
    assert "Could not parse valid YAML" in str(exc.value)
