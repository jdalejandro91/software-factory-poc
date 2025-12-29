import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from software_factory_poc.main import app
from software_factory_poc.infrastructure.entrypoints.api.jira_trigger_router import get_usecase
from software_factory_poc.application.usecases.scaffolding.process_jira_request_usecase import ProcessJiraRequestUseCase
from software_factory_poc.application.core.entities.scaffolding_agent import ScaffoldingAgent
from software_factory_poc.infrastructure.providers.knowledge.confluence_mock_adapter import ConfluenceMockAdapter
from software_factory_poc.infrastructure.providers.knowledge.architecture_constants import SHOPPING_CART_ARCHITECTURE
from software_factory_poc.application.core.interfaces.llm_gateway import LLMGatewayPort
from software_factory_poc.configuration.main_settings import Settings
from software_factory_poc.application.ports.tools.jira_provider import JiraProvider
from software_factory_poc.application.ports.tools.gitlab_provider import GitLabProvider

from software_factory_poc.infrastructure.entrypoints.api.jira_trigger_router import get_settings
from software_factory_poc.configuration.main_settings import Settings

# ... imports ...



class MockLLMGateway(LLMGatewayPort):
    def __init__(self):
        self.last_prompt = ""
        self.last_model = ""

    def generate_code(self, prompt: str, model: str) -> str:
        self.last_prompt = prompt
        self.last_model = model
        return '{"src/shopping_cart.py": "class ShoppingCart: pass"}'

mock_llm = MockLLMGateway()

@pytest.fixture(autouse=True)
def setup_overrides():

    def get_settings_override():
        s = Settings()
        from pydantic import SecretStr
        s.jira_webhook_secret = SecretStr("test-secret")
        return s

    def override_get_usecase_fn():
        # Use real Confluence Adapter to test integration
        kb_adapter = ConfluenceMockAdapter()
        
        # Use Mock LLM
        agent = ScaffoldingAgent(llm_gateway=mock_llm, knowledge_port=kb_adapter)
        
        # Mock Providers
        mock_jira = MagicMock(spec=JiraProvider)
        mock_gitlab = MagicMock(spec=GitLabProvider)
        
        # Setup GitLab Mock return values to avoid failures
        mock_gitlab.resolve_project_id.return_value = 123
        mock_gitlab.create_merge_request.return_value = {"web_url": "http://gitlab.mock/mr/1"}
        mock_gitlab.branch_exists.return_value = False # <--- Ensure standard flow proceeds
        
        settings = Settings()
        
        return ProcessJiraRequestUseCase(agent=agent, jira_provider=mock_jira, gitlab_provider=mock_gitlab, settings=settings)

    app.dependency_overrides[get_settings] = get_settings_override
    app.dependency_overrides[get_usecase] = override_get_usecase_fn
    yield
    app.dependency_overrides = {}

client = TestClient(app)

def test_jira_scaffolding_flow_end_to_end():
    payload = {
        "webhookEvent": "jira:issue_created",
        "timestamp": 123456789,
        "user": {
            "name": "tester",
            "displayName": "Integration Tester",
            "active": True
        },
        "issue": {
            "id": "1001",
            "key": "KAN-123",
            "fields": {
                "summary": "Implement Shopping Cart Feature",
                "description": """
Please create:
```scaffolding
version: '1.0'
technology_stack: python-api-v1
target:
  gitlab_project_path: 'mock-group/mock-project'
parameters:
  service_name: 'shopping-cart-service'
```
Instruction: Create a Python shopping cart with add_item method.
""",
                "project": {
                    "key": "KAN",
                    "name": "Kanban Project"
                }
            }
        }
    }

    # API Key from settings (default mock or env)
    # Using default secret from Settings() if not set env
    # Mock Env Vars for Settings
    msg_env = {
        "JIRA_WEBHOOK_SECRET": "test-secret", 
        "JIRA_USER_EMAIL": "test@example.com",
        "JIRA_API_TOKEN": "token",
        "JIRA_BASE_URL": "https://test.jira.com"
    }
    with pytest.MonkeyPatch.context() as mp:
        for k, v in msg_env.items():
            mp.setenv(k, v)
        
        settings = Settings()
        headers = {"X-API-Key": "test-secret"}
    
        response = client.post("/api/v1/jira-webhook", json=payload, headers=headers)

    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "accepted"
    
    # Verifications
    prompt = mock_llm.last_prompt
    
    # 1. Mapper Verification: Prompt contains instruction (YAML block)
    # Since JiraMapper extracts only the block, we verity the YAML content is present.
    assert "service_name: 'shopping-cart-service'" in prompt
    assert "mock-group/mock-project" in prompt
    
    # 2. Adapter Verification: Prompt contains Architecture Text
    assert "Shopping Cart Architecture (Modular Monolith)" in prompt
    assert "Cart Entity" in prompt
    
    # 3. Agent Verification: Constructed structure
    assert "INPUT CONTEXT (Architecture Pattern):" in prompt
    assert "USER REQUEST (Contains 'technology_stack' and 'parameters'):" in prompt
    
    # 4. Prompt Hardening Verification
    assert "CRITICAL RULES FOR GENERATION:" in prompt
    assert "ONE-SHOT EXAMPLE (Expected Behavior for a NestJS request):" in prompt
