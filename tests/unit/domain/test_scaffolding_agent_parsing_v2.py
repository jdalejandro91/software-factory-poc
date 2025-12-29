import pytest
import json
from unittest.mock import MagicMock
from software_factory_poc.application.core.entities.scaffolding_agent import ScaffoldingAgent, LLMOutputFormatError
from software_factory_poc.application.core.interfaces.llm_gateway import LLMGatewayPort
from software_factory_poc.application.core.ports.knowledge_base_port import KnowledgeBasePort

@pytest.fixture
def agent():
    mock_llm = MagicMock(spec=LLMGatewayPort)
    mock_kb = MagicMock(spec=KnowledgeBasePort)
    return ScaffoldingAgent(llm_gateway=mock_llm, knowledge_port=mock_kb)

def test_parse_clean_json(agent):
    valid_json = '{"file.txt": "content"}'
    result = agent._parse_response_to_files(valid_json)
    assert result == {"file.txt": "content"}

def test_parse_markdown_block(agent):
    markdown_json = '```json\n{"file.txt": "content"}\n```'
    result = agent._parse_response_to_files(markdown_json)
    assert result == {"file.txt": "content"}

def test_parse_markdown_no_lang(agent):
    markdown_json = '```\n{"file.txt": "content"}\n```'
    result = agent._parse_response_to_files(markdown_json)
    assert result == {"file.txt": "content"}

def test_parse_extra_text_fallback(agent):
    messy_text = 'Here is the code:\n{"file.txt": "content"}\nHope it helps!'
    result = agent._parse_response_to_files(messy_text)
    assert result == {"file.txt": "content"}

def test_parse_failure(agent):
    invalid_text = 'Not valid json'
    with pytest.raises(LLMOutputFormatError) as exc:
        agent._parse_response_to_files(invalid_text)
    assert "Model output is not valid JSON" in str(exc.value)

def test_parse_nested_braces_in_strings(agent):
    # Ensure regex/find logic doesn't break on braces inside strings
    complex_json = '{"file.js": "function test() { return true; }"}'
    result = agent._parse_response_to_files(complex_json)
    assert result == {"file.js": "function test() { return true; }"}
