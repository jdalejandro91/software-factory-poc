from unittest.mock import patch, MagicMock
from software_factory_poc.application.core.agents.scaffolding.scaffolding_agent import ScaffoldingAgent
from software_factory_poc.application.core.agents.common.dtos.file_content_dto import FileContentDTO
from software_factory_poc.application.core.agents.scaffolding.config.scaffolding_agent_config import ScaffoldingAgentConfig
from unittest.mock import patch, MagicMock

from software_factory_poc.application.core.agents.common.dtos.file_content_dto import FileContentDTO
from software_factory_poc.application.core.agents.scaffolding.config.scaffolding_agent_config import \
    ScaffoldingAgentConfig
from software_factory_poc.application.core.agents.scaffolding.scaffolding_agent import ScaffoldingAgent


def test_payload_sanitization():
    # Setup
    config = MagicMock(spec=ScaffoldingAgentConfig)
    agent = ScaffoldingAgent(config)
    
    artifacts = [
        FileContentDTO(path="/src/main.py", content="code"),
        FileContentDTO(path="README.md", content="docs")
    ]
    
    # Execute
    payload = agent._prepare_commit_payload(artifacts)
    
    # Verify
    assert "src/main.py" in payload
    assert "/src/main.py" not in payload
    assert "README.md" in payload

def test_payload_duplicates():
    # Setup
    config = MagicMock(spec=ScaffoldingAgentConfig)
    agent = ScaffoldingAgent(config)
    
    artifacts = [
        FileContentDTO(path="config.json", content="v1"),
        FileContentDTO(path="/config.json", content="v2")
    ]
    
    # Execute
    with patch("software_factory_poc.application.core.agents.scaffolding.scaffolding_agent.logger") as mock_logger:
        payload = agent._prepare_commit_payload(artifacts)
        
        # Verify
        assert payload["config.json"] == "v2" # Last write wins
        mock_logger.warning.assert_called_with("Duplicate path generated: config.json. Overwriting with latest content.")
