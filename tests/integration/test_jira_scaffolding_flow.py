import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from software_factory_poc.application.core.ports.gateways.dtos import TaskDTO, MergeRequestDTO, BranchDTO, CommitResultDTO
from software_factory_poc.application.core.domain.configuration.task_status import TaskStatus
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

    # 2. Setup Mocks via Patch with Strict Specs
    # using spec=True ensures calls fail if method doesn't exist on real class
    with patch("software_factory_poc.infrastructure.resolution.provider_resolver.ProviderResolver.resolve_llm_gateway", spec=True) as mock_resolve_llm, \
         patch("software_factory_poc.infrastructure.resolution.provider_resolver.ProviderResolver.resolve_vcs", spec=True) as mock_resolve_vcs, \
         patch("software_factory_poc.infrastructure.resolution.provider_resolver.ProviderResolver.resolve_tracker", spec=True) as mock_resolve_tracker, \
         patch("software_factory_poc.infrastructure.resolution.provider_resolver.ProviderResolver.resolve_knowledge", spec=True) as mock_resolve_knowledge:
        
        # Configure LLM Mock
        mock_llm_instance = MagicMock()
        mock_resolve_llm.return_value = mock_llm_instance
        
        # Return an object that has .content attribute (LlmResponse-like)
        mock_response = MagicMock()
        mock_response.content = (
            "<<<FILE:src/shopping_cart.py>>>\n"
            "class ShoppingCart: pass\n"
            "<<<END>>>"
        )
        mock_llm_instance.generate_code.return_value = mock_response
        
        # Configure VCS Mock (Strict DTOs)
        # Note: mocking the instance returned by resolve_vcs directly
        mock_vcs_instance = MagicMock()
        mock_resolve_vcs.return_value = mock_vcs_instance
        mock_vcs_instance.branch_exists.return_value = False 
        # Using manual DTO instantiation or factory if I injected it. 
        # Here I will just instantiate DTOs directly as it's cleaner than injecting fixture into this big block.
        mock_vcs_instance.create_merge_request.return_value = MergeRequestDTO(id="1", web_url="http://gitlab.mock/mr/1")
        mock_vcs_instance.create_branch.return_value = BranchDTO("feature/KAN-123/scaffolding", "url")
        mock_vcs_instance.commit_files.return_value = CommitResultDTO("sha", "url")
        
        # Configure Tracker Mock (Jira)
        mock_tracker_instance = MagicMock()
        mock_resolve_tracker.return_value = mock_tracker_instance
        
        # Configure Knowledge Mock
        mock_knowledge_instance = MagicMock()
        mock_resolve_knowledge.return_value = mock_knowledge_instance
        mock_knowledge_instance.retrieve_context.return_value = "Shopping Cart Architecture (Modular Monolith)\nCart Entity"
        mock_knowledge_instance.retrieve_similar_solutions.return_value = "Examples"
        
        # 3. Execution
        headers = {"X-API-Key": "test-secret"}
        
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("JIRA_WEBHOOK_SECRET", "test-secret")
            
            response = client.post("/api/v1/jira-webhook", json=payload, headers=headers)
            
            # 4. Verifications
            assert response.status_code == 202
            assert response.json()["status"] == "accepted"
            
            # Verification 1: LLM Interaction
            assert mock_llm_instance.generate_code.called
            
            # Inspect Prompt
            call_args = mock_llm_instance.generate_code.call_args
            args, kwargs = call_args
            prompt_arg = args[0] if args else kwargs.get("prompt")
            
            assert "service_name: 'shopping-cart-service'" in prompt_arg
            assert "Shopping Cart Architecture" in prompt_arg
            
            # Verification 2: Tracker Interaction with Strict Sequence
            from unittest.mock import call, ANY
            
            # Use strict assert_has_calls to check order: Report Start -> Report Success
            mock_tracker_instance.add_comment.assert_has_calls([
                call("KAN-123", ANY), # Start
                call("KAN-123", ANY)  # Success
            ])
            
            # Verify Transition
            mock_tracker_instance.transition_status.assert_has_calls([
                call("KAN-123", TaskStatus.IN_REVIEW)
            ])

