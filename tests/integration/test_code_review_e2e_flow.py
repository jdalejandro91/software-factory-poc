
from unittest.mock import MagicMock, patch, AsyncMock
import pytest
from fastapi.testclient import TestClient
from software_factory_poc.main import app

client = TestClient(app)

@pytest.fixture
def mock_settings():
    with patch("software_factory_poc.infrastructure.entrypoints.api.security.Settings") as MockSettings:
        settings = MagicMock()
        settings.jira_webhook_secret.get_secret_value.return_value = "test-secret"
        MockSettings.return_value = settings
        yield settings

def test_code_review_e2e_flow_success(mock_settings):
    """
    E2E Test ensuring ProviderResolver correctly wires dependencies for PerformCodeReviewUseCase.
    Mocks mostly external provider clients (Jira, GitLab, LLM) but keeps the Resolver/UseCase real.
    """
    import textwrap

    # 1. Mock External Adapters/Providers to avoid real network calls
    # We patch at the 'ProviderResolver' resolution level or the specific clients used by providers.
    # To test wiring, we should probably patch the CLIENTS, not the Providers, 
    # but some Providers are instantiated inside resolver.create_X().
    
    # Let's verify what ProviderResolver instantiates. 
    # It creates JiraProviderImpl, GitLabProviderImpl, CompositeLlmGateway, etc.
    # We want to ensure proper instantiation (solving TypeErrors). 
    # If we mock create_code_reviewer_agent, we miss the point.
    
    # We will patch the HTTP Clients and Factories used by the Providers/Resolver.
    # We ALSO need to patch AppConfig in the router because it instantiates it directly.
    
    with patch("software_factory_poc.infrastructure.resolution.provider_resolver.JiraHttpClient") as MockJiraClient, \
         patch("software_factory_poc.infrastructure.resolution.provider_resolver.GitLabHttpClient") as MockGitLabClient, \
         patch("software_factory_poc.infrastructure.resolution.provider_resolver.LlmProviderFactory") as MockLlmFactory, \
         patch("software_factory_poc.infrastructure.entrypoints.api.code_review_router.AppConfig") as MockRouterAppConfig:
         
        # Setup Mock AppConfig (critical for Resolver logic)
        mock_app_config_instance = MockRouterAppConfig.return_value
        mock_app_config_instance.tools.code_review_model = "gpt-4-turbo"
        mock_app_config_instance.tools.code_review_llm_model_priority = '["openai:gpt-4-turbo"]'
        
        # Setup Mock Clients
        mock_jira_client = MockJiraClient.return_value
        mock_gitlab_client = MockGitLabClient.return_value
        
        # Setup Mock LLM Gateway
        mock_llm_gateway = MagicMock()
        # LlmProviderFactory.build_providers returns a Dict[LlmProviderType, LlmProvider]
        # We need to mock the keys likely being LlmProviderType enum.
        # However, checking the failure `registered_providers = [p.value for p in clients.keys()]`, 
        # implies keys are Enums with a .value property.
        
        # We'll use a simple mock object for the key that has a .value
        mock_provider_type = MagicMock()
        mock_provider_type.value = "openai"
        
        MockLlmFactory.build_providers.return_value = {mock_provider_type: mock_llm_gateway}
        
        # 2. Define Payload with nested params
        description = textwrap.dedent("""
        Review this change.
        ```yaml
        code_review_params:
          gitlab_project_id: '101'
          source_branch_name: 'feature/e2e-wire'
          mr_id: '88'
        ```
        """).strip()
        
        payload = {
            "issue": {
                "key": "CR-E2E-1",
                "fields": {
                    "summary": "E2E Code Review Check",
                    "description": description
                }
            },
            "user": {
                "name": "e2e-user",
                "displayName": "E2E User"
            }
        }
        
        # 3. Request
        # Note: BackgroundTasks will run PerformCodeReviewUseCase.execute()
        # We need to verify that 'execute' runs without crashing due to wiring.
        # TestClient runs background tasks synchronously by default.
        
        # HOWEVER, if PerformCodeReviewUseCase fails, it logs critical error and raises.
        # Background task failures might be suppressed by Starlette unless we catch them.
        # But logging should show up.
        
        # To strictly verify success, we can mock the actual 'CodeReviewerAgent.execute_flow' 
        # because we want to verify Wiring up TO that point. 
        # OR we let it run and mock the LLM calls to return dummy data.
        
        # The prompt asks to "reproduce possible TypeErrors in instantiation". 
        # So we just need to ensure request acceptance and that the use case starts.
        
        # We will Mock UseCase.execute to verify correct instantiation of UseCase itself?
        # No, the Prompt says "keep UseCases real". 
        # So UseCase.execute will run. It calls self.resolver.create_reporter_agent... etc.
        # Then it builds Collaborators and calls orchestrator.execute_flow.
        
        # We should patch 'CodeReviewerAgent.execute_flow' to stop execution there 
        # but prove that everything UP TO that point (wiring) worked.
        
        headers = {"X-API-KEY": "test-secret"}
        
        with patch("software_factory_poc.application.core.agents.code_reviewer.code_reviewer_agent.CodeReviewerAgent.execute_flow") as mock_execute_flow:    
            response = client.post(
                "/api/v1/webhooks/jira/code-review-trigger", 
                json=payload, 
                headers=headers
            )
            
            assert response.status_code == 202
            assert response.json()["message"] == "Code Review request queued."
            
            # 4. Verification
            # If wiring is correct, execute_flow should be called.
            # If wiring is broken (TypeError in Resolver), execution crashes before this.
            
            assert mock_execute_flow.called
            task_arg = mock_execute_flow.call_args[0][0]
            
            # Verify correct extraction
            config = task_arg.description.config.get("code_review_params", {})
            assert config["gitlab_project_id"] == "101"
            assert config["source_branch_name"] == "feature/e2e-wire"
