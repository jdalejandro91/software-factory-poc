
import pytest
from unittest.mock import MagicMock
from software_factory_poc.application.usecases.scaffolding.create_scaffolding_usecase import CreateScaffoldingUseCase
from software_factory_poc.application.core.domain.entities.scaffolding.scaffolding_request import ScaffoldingRequest
from software_factory_poc.application.core.domain.entities.scaffolding.scaffolding_agent import ScaffoldingAgent
from software_factory_poc.application.core.ports.gateways.knowledge_gateway import KnowledgeGateway
from software_factory_poc.application.core.ports.gateways.task_tracker_gateway_port import TaskTrackerGatewayPort


class TestKnowledgeIntegration:
    def test_knowledge_context_logging(self, caplog):
        # Setup Mocks
        config_mock = MagicMock()
        resolver_mock = MagicMock()
        
        tracker_mock = MagicMock(spec=TaskTrackerGatewayPort)
        knowledge_mock = MagicMock(spec=KnowledgeGateway)
        vcs_mock = MagicMock()
        llm_mock = MagicMock()
        
        resolver_mock.resolve_tracker.return_value = tracker_mock
        resolver_mock.resolve_knowledge.return_value = knowledge_mock
        resolver_mock.resolve_vcs.return_value = vcs_mock
        resolver_mock.resolve_llm_gateway.return_value = llm_mock
        
        # VCS Mock to pass branch check
        vcs_mock.resolve_project_id.return_value = "123"
        vcs_mock.branch_exists.return_value = False
        
        # Knowledge Mock to return text
        knowledge_mock.retrieve_context.return_value = "A" * 150 # 150 chars, should be INFO
        
        # LLM Mock to allow flow completion
        llm_mock.generate_code.return_value = "<<<FILE:README.md>>>\nTest\n<<<END>>>"

        usecase = CreateScaffoldingUseCase(config_mock, resolver_mock)
        request = ScaffoldingRequest(
            issue_key="TEST-KNOW",
            summary="Test Knowledge",
            raw_instruction="Do it",
            reporter="Tester",
            technology_stack="python"
        )
        
        with caplog.at_level('INFO'):
            usecase.execute(request)
            
        # Verify Logs
        assert "Confluence knowledge retrieved. Size: 150 chars." in caplog.text
        # Verify Query construction (including page_id)
        knowledge_mock.retrieve_context.assert_called_with("python Test Knowledge page_id:3571713")
        
    def test_knowledge_context_warning_if_small(self, caplog):
        # Setup Mocks
        config_mock = MagicMock()
        resolver_mock = MagicMock()
        
        tracker_mock = MagicMock(spec=TaskTrackerGatewayPort)
        knowledge_mock = MagicMock(spec=KnowledgeGateway)
        vcs_mock = MagicMock()
        llm_mock = MagicMock()
        
        resolver_mock.resolve_tracker.return_value = tracker_mock
        resolver_mock.resolve_knowledge.return_value = knowledge_mock
        resolver_mock.resolve_vcs.return_value = vcs_mock
        resolver_mock.resolve_llm_gateway.return_value = llm_mock
        
        vcs_mock.resolve_project_id.return_value = "123"
        vcs_mock.branch_exists.return_value = False
        
        # Knowledge Mock to return tiny text
        knowledge_mock.retrieve_context.return_value = "Tiny context" 
        llm_mock.generate_code.return_value = "<<<FILE:README.md>>>\nTest\n<<<END>>>"

        usecase = CreateScaffoldingUseCase(config_mock, resolver_mock)
        request = ScaffoldingRequest(
            issue_key="TEST-WARN",
            summary="Test Knowledge Warn",
            raw_instruction="Do it",
            reporter="Tester",
            technology_stack="python"
        )
        
        with caplog.at_level('WARNING'):
            usecase.execute(request)
            
        assert "Suspiciously small knowledge context retrieved (<100 chars)." in caplog.text
