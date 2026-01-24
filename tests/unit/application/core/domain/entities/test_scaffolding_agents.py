import pytest
from software_factory_poc.application.core.domain.entities.scaffolding.scaffolding_agent import ScaffoldingAgent
from software_factory_poc.application.core.domain.entities.scaffolding.scaffolding_agent_config import ScaffoldingAgentConfig
from software_factory_poc.application.core.domain.entities.agents.vcs_agent import VcsAgent
from software_factory_poc.application.core.domain.entities.agents.reporter_agent import ReporterAgent
from software_factory_poc.application.core.domain.entities.agents.knowledge_agent import KnowledgeAgent

def test_scaffolding_agent_config_creation():
    config = ScaffoldingAgentConfig(model_name="gpt-4", temperature=0.7)
    assert config.model_name == "gpt-4"
    assert config.temperature == 0.7
    assert config.extra_params == {}

def test_scaffolding_agent_creation():
    config = ScaffoldingAgentConfig(model_name="test-model")
    agent = ScaffoldingAgent(
        agent_id="agent-123",
        name="Scaffolder",
        role="Architect",
        goal="Create scaffolding",
        config=config
    )
    
    assert agent.agent_id == "agent-123"
    assert agent.name == "Scaffolder"
    assert agent.role == "Architect"
    assert agent.goal == "Create scaffolding"
    assert agent.config == config

def test_vcs_agent_is_abstract():
    with pytest.raises(TypeError):
        VcsAgent()

def test_reporter_agent_is_abstract():
    with pytest.raises(TypeError):
        ReporterAgent()

def test_knowledge_agent_is_abstract():
    with pytest.raises(TypeError):
        KnowledgeAgent()

def test_scaffolding_agent_no_longer_has_behavior_methods():
    config = ScaffoldingAgentConfig()
    agent = ScaffoldingAgent("id", "name", "role", "goal", config)
    
    # Ensure old methods are gone
    assert not hasattr(agent, "search_knowledge")
    assert not hasattr(agent, "build_prompt")
    assert not hasattr(agent, "report_success")
