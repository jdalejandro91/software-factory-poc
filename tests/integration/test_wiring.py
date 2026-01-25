import os
import pytest
from software_factory_poc.configuration.app_config import AppConfig
from software_factory_poc.infrastructure.resolution.provider_resolver import ProviderResolver
from software_factory_poc.infrastructure.configuration.scaffolding_config_loader import ScaffoldingConfigLoader
from software_factory_poc.application.core.domain.agents.research.config.research_provider_type import ResearchProviderType
from software_factory_poc.infrastructure.providers.research.confluence_provider_impl import ConfluenceProviderImpl
from software_factory_poc.application.core.domain.agents.research.ports.research_gateway import ResearchGateway
from software_factory_poc.application.usecases.scaffolding.create_scaffolding_usecase import CreateScaffoldingUseCase
from software_factory_poc.application.core.domain.agents.research.research_agent import ResearchAgent

def test_wiring_confluence_provider():
    # 1. Setup Env Vars
    os.environ["SCAFFOLDING_RESEARCH_PROVIDER"] = "CONFLUENCE"
    os.environ["CONFLUENCE_USER_EMAIL"] = "test@example.com"
    os.environ["CONFLUENCE_API_TOKEN"] = "secret"
    os.environ["CONFLUENCE_BASE_URL"] = "https://example.atlassian.net"
    os.environ["CONFLUENCE_ARCHITECTURE_DOC_PAGE_ID"] = "12345"
    
    # 2. Load Configs
    scaffolding_config = ScaffoldingConfigLoader.load_config()
    app_config = AppConfig()
    
    assert scaffolding_config.research_provider == ResearchProviderType.CONFLUENCE
    assert app_config.confluence.user_email == "test@example.com"
    
    # 3. Instantiate Resolver
    resolver = ProviderResolver(scaffolding_config, app_config=app_config)
    
    # 4. Resolve Research Gateway
    gateway = resolver.resolve_research()
    
    assert isinstance(gateway, ConfluenceProviderImpl)
    assert isinstance(gateway, ResearchGateway)
    assert gateway.settings.architecture_doc_page_id == "12345"
    
    # 5. Instantiate Use Case (Full Wiring)
    usecase = CreateScaffoldingUseCase(scaffolding_config, resolver)
    
    # Note: We can't easily inspect the internal agents of usecase unless we access them during execution or if they are public.
    # The Usecase instantiates agents inside `execute`, they are NOT attributes of the usecase class.
    # But we can verify `resolver.resolve_research()` worked.
    # The usecase executes `resolver.resolve_research()` in `execute()`.
    
    # Check `resolve_research` is consistent
    gateway2 = resolver.resolve_research()
    assert isinstance(gateway2, ConfluenceProviderImpl)

def test_research_agent_integration_logic():
    # Test strict logic: Integration test of Agent + Provider without real HTTP calls (mocked settings/client)
    # But here we want to test WIRING. Use verify_wiring type tests.
    pass
