
import pytest
from unittest.mock import MagicMock, ANY
from software_factory_poc.application.usecases.scaffolding.create_scaffolding_usecase import CreateScaffoldingUseCase
from software_factory_poc.application.core.domain.entities.scaffolding.scaffolding_request import ScaffoldingRequest
from software_factory_poc.application.core.ports.gateways.task_tracker_gateway_port import TaskTrackerGatewayPort

class TestFailSafeReporting:
    def test_reports_failure_when_resolution_fails(self):
        # Setup Mocks
        config_mock = MagicMock()
        resolver_mock = MagicMock()
        
        tracker_mock = MagicMock(spec=TaskTrackerGatewayPort)
        resolver_mock.resolve_tracker.return_value = tracker_mock
        
        # Simular fallo en VCS (ej. GitHub no implementado)
        resolver_mock.resolve_vcs.side_effect = NotImplementedError("GitHub Adapter Not Found")
        
        usecase = CreateScaffoldingUseCase(config_mock, resolver_mock)
        
        request = ScaffoldingRequest(
            issue_key="TEST-123",
            summary="Test",
            raw_instruction="",
            reporter="Test User",
            technology_stack="python",
        )
        
        # Execute
        usecase.execute(request)
        
        # Assert Tracker was called to report failure
        # We need to verify that report_failure -> transition_status or add_comment was called.
        # ScaffoldingAgent.report_failure calls:
        # 1. tracker.add_comment
        # 2. tracker.transition_status (BACKLOG/TO_DO default)
        
        tracker_mock.add_comment.assert_called()
        # Check call arguments to confirm it contains the error
        args, _ = tracker_mock.add_comment.call_args
        assert args[0] == "TEST-123"
        assert "GitHub Adapter Not Found" in str(args[1]) or "GitHub Adapter Not Found" in str(args[1].get('body', ''))

    def test_returns_early_invalid_tracker(self):
        # Scenario: Even Tracker resolution fails
        config_mock = MagicMock()
        resolver_mock = MagicMock()
        resolver_mock.resolve_tracker.side_effect = Exception("Tracker Connection Failed")
        
        usecase = CreateScaffoldingUseCase(config_mock, resolver_mock)
        request = ScaffoldingRequest(issue_key="TEST-DEAD",summary="X",raw_instruction="",reporter="X",technology_stack="X")
        
        # Should not raise exception (fail silent but log critical)
        usecase.execute(request)
        
        # Verify nothing exploded
        resolver_mock.resolve_vcs.assert_not_called()
