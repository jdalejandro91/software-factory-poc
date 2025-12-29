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

client = TestClient(app)

class MockLLMGateway(LLMGatewayPort):
    def __init__(self):
        self.last_prompt = ""
        self.last_model = ""

    def generate_code(self, prompt: str, model: str) -> str:
        self.last_prompt = prompt
        self.last_model = model
        return '{"src/shopping_cart.py": "class ShoppingCart: pass"}'

mock_llm = MockLLMGateway()

def override_get_usecase():
    # Use real Confluence Adapter to test integration
    kb_adapter = ConfluenceMockAdapter()
    
    # Use Mock LLM
    agent = ScaffoldingAgent(llm_gateway=mock_llm, knowledge_port=kb_adapter)
    
    # Override URL to hit the logic "carrito-de-compra"
    # Wait, the Agent has hardcoded URL in __init__.
    # But checking Agent __init__, it uses self._knowledge_url.
    # We can patch it or rely on the fact that ConfluenceMockAdapter handles checking "carrito-de-compra".
    # The requirement said "Si la URL contiene 'carrito-de-compra'".
    # The agent's hardcoded URL is "https://.../Shopping+Cart+Architecture".
    # Does generic "Shopping+Cart" match "carrito-de-compra"?
    # I should check Agent implementation of URL.
    # In Step 1502: self._knowledge_url = "https://confluence.corp.com/wiki/spaces/ARCH/pages/Shopping+Cart+Architecture"
    # ConfluenceMockAdapter in Step 1507 checks: if "carrito-de-compra" in url.
    # "Shopping+Cart" does NOT contain "carrito-de-compra".
    # I MUST update the Agent's URL or Adapter's check or inject a URL that matches.
    # The user requirement for Adapter was: "Si la URL contiene 'carrito-de-compra'".
    
    # Mock Providers
    mock_jira = MagicMock(spec=JiraProvider)
    mock_gitlab = MagicMock(spec=GitLabProvider)
    
    # Setup GitLab Mock return values to avoid failures
    mock_gitlab.resolve_project_id.return_value = 123
    mock_gitlab.create_merge_request.return_value = {"web_url": "http://gitlab.mock/mr/1"}
    
    return ProcessJiraRequestUseCase(agent=agent, jira_provider=mock_jira, gitlab_provider=mock_gitlab)

app.dependency_overrides[get_usecase] = override_get_usecase

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
template: python-api-v1
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
    settings = Settings()
    headers = {"X-API-Key": settings.jira_webhook_secret.get_secret_value()}

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
    assert "INPUT CONTEXT:" in prompt
    assert "USER REQUEST:" in prompt
