from unittest.mock import MagicMock, ANY
import pytest
from software_factory_poc.application.usecases.scaffolding.create_scaffolding_usecase import CreateScaffoldingUseCase
from software_factory_poc.application.core.domain.entities.scaffolding.scaffolding_request import ScaffoldingRequest
from software_factory_poc.application.usecases.scaffolding.agent_adapters import VcsAgentAdapter, ReporterAgentAdapter, KnowledgeAgentAdapter
from software_factory_poc.application.core.domain.entities.scaffolding.scaffolding_agent import ScaffoldingAgent

class TestCreateScaffoldingUseCase:
    def test_delegates_to_agent_on_success(self):
        # Mocks
        config_mock = MagicMock()
        resolver_mock = MagicMock()
        
        # Resolvers return mocks
        resolver_mock.resolve_tracker.return_value = MagicMock()
        resolver_mock.resolve_vcs.return_value = MagicMock()
        resolver_mock.resolve_knowledge.return_value = MagicMock()
        resolver_mock.resolve_llm_gateway.return_value = MagicMock()
        
        usecase = CreateScaffoldingUseCase(config_mock, resolver_mock)
        
        # Mock the usecase.agent.execute_scaffolding_flow 
        # Since 'agent' is created in __init__, we need to patch it or mock it.
        # But 'ScaffoldingAgent' is a dataclass now, so 'agent' attribute is just a dataclass instance.
        # Wait, CreateScaffoldingUseCase instantiates `ScaffoldingAgent()` inside `__init__`.
        # I need to mock that instance's `execute_scaffolding_flow` method.
        
        # IMPORTANT: Since `ScaffoldingAgent` is a dataclass but I added a method to it, 
        # simpler way is to assign a mock to `usecase.agent.execute_scaffolding_flow`.
        usecase.agent.execute_scaffolding_flow = MagicMock()

        request = ScaffoldingRequest(
            issue_key="TEST-1",
            summary="Test",
            raw_instruction="",
            reporter="User",
            technology_stack="Python"
        )
        
        # Execute
        usecase.execute(request)
        
        # Assertions
        resolver_mock.resolve_tracker.assert_called()
        resolver_mock.resolve_vcs.assert_called()
        resolver_mock.resolve_knowledge.assert_called()
        resolver_mock.resolve_llm_gateway.assert_called()
        
        usecase.agent.execute_scaffolding_flow.assert_called_once()
        args, kwargs = usecase.agent.execute_scaffolding_flow.call_args
        assert kwargs['request'] == request
        assert isinstance(kwargs['reporter'], ReporterAgentAdapter)
        assert isinstance(kwargs['vcs'], VcsAgentAdapter)
        assert isinstance(kwargs['knowledge'], KnowledgeAgentAdapter)

    def test_handles_dependency_resolution_errors(self):
        # Setup mocks to fail resolution
        resolver_mock = MagicMock()
        resolver_mock.resolve_tracker.side_effect = Exception("Tracker dead")
        
        usecase = CreateScaffoldingUseCase(MagicMock(), resolver_mock)
        
        request = ScaffoldingRequest("TEST-FAIL", "X", "X", "X", "X")
        
        # Should not raise
        usecase.execute(request)
        
        # Should have logged critical error (not verifying logs here for simplicity, assuming no crash)
