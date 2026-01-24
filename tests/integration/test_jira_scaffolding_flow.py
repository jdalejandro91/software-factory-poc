import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from software_factory_poc.main import app
from software_factory_poc.infrastructure.configuration.main_settings import Settings

client = TestClient(app)

def test_jira_scaffolding_flow_end_to_end():
    # 1. Prepare Payload
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
        },
        "changelog": {
            "id": "9999",
            "items": [
                {
                    "field": "status",
                    "fieldtype": "jira",
                    "fromString": "Por hacer",
                    "toString": "En curso"
                }
            ]
        }
    }

    # 2. Setup Mocks via Patch (Robust Strategy)
    # We patch the Resolver methods to return our controlled Mocks regardless of lifecycle
    with patch("software_factory_poc.infrastructure.resolution.provider_resolver.ProviderResolver.resolve_llm_gateway") as mock_resolve_llm, \
         patch("software_factory_poc.infrastructure.resolution.provider_resolver.ProviderResolver.resolve_vcs") as mock_resolve_vcs, \
         patch("software_factory_poc.infrastructure.resolution.provider_resolver.ProviderResolver.resolve_tracker") as mock_resolve_tracker, \
         patch("software_factory_poc.infrastructure.resolution.provider_resolver.ProviderResolver.resolve_knowledge") as mock_resolve_knowledge:
        
        # Configure LLM Mock
        mock_llm_instance = MagicMock()
        mock_resolve_llm.return_value = mock_llm_instance
        # Return a valid block so parsing doesn't fail
        mock_llm_instance.generate_code.return_value = (
            "<<<FILE:src/shopping_cart.py>>>\n"
            "class ShoppingCart: pass\n"
            "<<<END>>>"
        )
        
        # Configure VCS Mock
        mock_vcs_instance = MagicMock()
        mock_resolve_vcs.return_value = mock_vcs_instance
        # Simulate branch does not exist so flow proceeds
        mock_vcs_instance.branch_exists.return_value = False 
        mock_vcs_instance.create_merge_request.return_value = {"web_url": "http://gitlab.mock/mr/1"}
        
        # Configure Tracker Mock (Jira)
        mock_tracker_instance = MagicMock()
        mock_resolve_tracker.return_value = mock_tracker_instance
        
        # Configure Knowledge Mock
        mock_knowledge_instance = MagicMock()
        mock_resolve_knowledge.return_value = mock_knowledge_instance
        mock_knowledge_instance.retrieve_context.return_value = "Shopping Cart Architecture (Modular Monolith)\nCart Entity"
        
        # 3. Execution
        # Mock Env headers for auth check
        headers = {"X-API-Key": "test-secret"}
        
        # We also need to ensure settings validation passes if secret is checked.
        # But for this integration test, assuming we have a valid secret or we mock settings.
        # Let's mock the secret env var just in case using MonkeyPatch context
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("JIRA_WEBHOOK_SECRET", "test-secret")
            
            # The API Router typically instantiates Settings() which reads env.
            response = client.post("/api/v1/jira-webhook", json=payload, headers=headers)
            
            # 4. Verifications
            assert response.status_code == 202
            assert response.json()["status"] == "accepted"
            
            # Verification 1: LLM Interaction
            # Check (assert_called) instead of global variable
            assert mock_llm_instance.generate_code.called
            
            # Inspect the prompt passed to LLM
            call_args = mock_llm_instance.generate_code.call_args
            # access (args, kwargs) from call_args
            args, kwargs = call_args
            prompt_arg = args[0] if args else kwargs.get("prompt")
            
            # 1. Mapper Verification: Prompt contains instruction
            assert "service_name: 'shopping-cart-service'" in prompt_arg
            assert "mock-group/mock-project" in prompt_arg
            
            # 2. Adapter Verification: Prompt contains Architecture Text (from Knowledge Mock)
            assert "Shopping Cart Architecture (Modular Monolith)" in prompt_arg
            assert "Cart Entity" in prompt_arg
            
            # 3. Agent Verification: Constructed structure
            assert "--- ARCHITECTURAL STANDARDS (RAG CONTEXT) ---" in prompt_arg
            assert "--- TASK INSTRUCTIONS ---" in prompt_arg
            
            # 4. Prompt Hardening Verification
            assert "--- CRITICAL OUTPUT RULES ---" in prompt_arg
            assert "--- EXAMPLE OUTPUT ---" in prompt_arg
            
            # Verification 2: Tracker Interaction
            # Check that success comment was posted
            mock_tracker_instance.add_comment.assert_called()
            # Check transition to IN_REVIEW or DONE
            mock_tracker_instance.transition_status.assert_called()

